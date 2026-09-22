from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.feed_window import FeedWindow
from app.models.hatchery import Hatchery
from app.models.pond import Pond
from app.models.user import User
from app.schemas.pond import PondCreate, PondUpdate, PondOut

router = APIRouter(prefix="/api/ponds", tags=["ponds"])


def _open_pond_ids(db: Session) -> set[int]:
    """当前时刻处于启用投喂窗的塘口 id 集合（与 /api/feed-windows/open 同口径）。"""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(FeedWindow.pond_id)
        .filter(
            FeedWindow.enabled.is_(True),
            FeedWindow.start_at <= now,
            FeedWindow.end_at >= now,
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def _attach_window_flag(pond: Pond, open_ids: set[int]) -> Pond:
    pond.in_feed_window = pond.id in open_ids
    return pond


@router.get("", response_model=List[PondOut])
def list_ponds(
    hatchery_id: Optional[int] = Query(None, alias="hatcheryId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Pond)
    if hatchery_id is not None:
        q = q.filter(Pond.hatchery_id == hatchery_id)
    ponds = q.order_by(Pond.id).all()
    open_ids = _open_pond_ids(db)
    return [_attach_window_flag(p, open_ids) for p in ponds]


@router.post("", response_model=PondOut, status_code=status.HTTP_201_CREATED)
def create_pond(
    payload: PondCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    hatchery = db.query(Hatchery).filter(Hatchery.id == payload.hatchery_id).first()
    if not hatchery:
        raise HTTPException(status_code=400, detail="育苗场不存在")
    item = Pond(
        hatchery_id=payload.hatchery_id,
        pond_code=payload.pond_code,
        species=payload.species,
        volume_m3=payload.volume_m3,
        status=payload.status,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同场塘口号已存在")
    db.refresh(item)
    return _attach_window_flag(item, _open_pond_ids(db))


@router.get("/{pond_id}", response_model=PondOut)
def get_pond(
    pond_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(Pond).filter(Pond.id == pond_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="塘口不存在")
    return _attach_window_flag(item, _open_pond_ids(db))


@router.put("/{pond_id}", response_model=PondOut)
def update_pond(
    pond_id: int,
    payload: PondUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(Pond).filter(Pond.id == pond_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="塘口不存在")
    data = payload.model_dump(exclude_unset=True)
    if "hatchery_id" in data:
        hatchery = db.query(Hatchery).filter(Hatchery.id == data["hatchery_id"]).first()
        if not hatchery:
            raise HTTPException(status_code=400, detail="育苗场不存在")
    for k, v in data.items():
        setattr(item, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同场塘口号已存在")
    db.refresh(item)
    return _attach_window_flag(item, _open_pond_ids(db))


@router.delete("/{pond_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pond(
    pond_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(Pond).filter(Pond.id == pond_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="塘口不存在")
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="该塘口仍有关联记录，无法删除")
