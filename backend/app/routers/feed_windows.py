from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.feeding_rules import has_window_overlap
from app.models.feed_window import FeedWindow
from app.models.pond import Pond
from app.models.user import User
from app.schemas.feed_window import FeedWindowCreate, FeedWindowOut, FeedWindowUpdate

router = APIRouter(prefix="/api/feed-windows", tags=["feed-windows"])


def _validate_window(db: Session, pond_id: int, start_at, end_at, exclude_id: Optional[int] = None):
    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="结束时刻必须晚于开始时刻")
    if not db.query(Pond).filter(Pond.id == pond_id).first():
        raise HTTPException(status_code=400, detail="塘口不存在")
    if has_window_overlap(db, pond_id, start_at, end_at, exclude_id=exclude_id):
        raise HTTPException(status_code=409, detail="同塘口投喂窗口时间段相交")


@router.get("", response_model=List[FeedWindowOut])
def list_windows(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(FeedWindow)
    if pond_id is not None:
        q = q.filter(FeedWindow.pond_id == pond_id)
    return q.order_by(FeedWindow.pond_id, FeedWindow.start_at).all()


@router.post("", response_model=FeedWindowOut, status_code=status.HTTP_201_CREATED)
def create_window(
    payload: FeedWindowCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _validate_window(db, payload.pond_id, payload.start_at, payload.end_at)
    item = FeedWindow(
        pond_id=payload.pond_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        enabled=payload.enabled,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{window_id}", response_model=FeedWindowOut)
def update_window(
    window_id: int,
    payload: FeedWindowUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(FeedWindow).filter(FeedWindow.id == window_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="投喂窗口不存在")
    data = payload.model_dump(exclude_unset=True)
    pond_id = data.get("pond_id", item.pond_id)
    start_at = data.get("start_at", item.start_at)
    end_at = data.get("end_at", item.end_at)
    _validate_window(db, pond_id, start_at, end_at, exclude_id=item.id)
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_window(
    window_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(FeedWindow).filter(FeedWindow.id == window_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="投喂窗口不存在")
    db.delete(item)
    db.commit()
