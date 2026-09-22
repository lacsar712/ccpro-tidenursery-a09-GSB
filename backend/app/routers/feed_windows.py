from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.feed_window import FeedWindow
from app.models.pond import Pond
from app.models.user import User
from app.schemas.feed_window import FeedWindowCreate, FeedWindowOut, FeedWindowUpdate

router = APIRouter(prefix="/api/feed-windows", tags=["feed-windows"])


def _intersects(
    db: Session,
    pond_id: int,
    start_at: datetime,
    end_at: datetime,
    exclude_id: Optional[int] = None,
) -> bool:
    """同塘口窗口时间轴按闭区间相交即冲突（含停用窗口，保证重新启用也不相交）。"""
    q = db.query(FeedWindow).filter(
        FeedWindow.pond_id == pond_id,
        FeedWindow.start_at <= end_at,
        FeedWindow.end_at >= start_at,
    )
    if exclude_id is not None:
        q = q.filter(FeedWindow.id != exclude_id)
    return db.query(q.exists()).scalar()


@router.get("", response_model=List[FeedWindowOut])
def list_windows(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(FeedWindow)
    if pond_id is not None:
        q = q.filter(FeedWindow.pond_id == pond_id)
    return q.order_by(FeedWindow.start_at.desc()).all()


@router.get("/open", response_model=List[FeedWindowOut])
def list_open_windows(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """当前时刻处于启用状态的投喂窗口；每塘至多一条（同塘窗口禁止相交）。"""
    now = datetime.now(timezone.utc)
    return (
        db.query(FeedWindow)
        .filter(
            FeedWindow.enabled.is_(True),
            FeedWindow.start_at <= now,
            FeedWindow.end_at >= now,
        )
        .order_by(FeedWindow.pond_id, FeedWindow.start_at)
        .all()
    )


@router.post("", response_model=FeedWindowOut, status_code=status.HTTP_201_CREATED)
def create_window(
    payload: FeedWindowCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")
    if _intersects(db, payload.pond_id, payload.start_at, payload.end_at):
        raise HTTPException(status_code=409, detail="同塘口投喂窗口时间相交")
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


@router.patch("/{window_id}", response_model=FeedWindowOut)
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
    if not db.query(Pond).filter(Pond.id == pond_id).first():
        raise HTTPException(status_code=400, detail="塘口不存在")
    if end_at <= start_at:
        raise HTTPException(status_code=400, detail="结束时刻必须晚于开始时刻")
    if _intersects(db, pond_id, start_at, end_at, exclude_id=window_id):
        raise HTTPException(status_code=409, detail="同塘口投喂窗口时间相交")
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
