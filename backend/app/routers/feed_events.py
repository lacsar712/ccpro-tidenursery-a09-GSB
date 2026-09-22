from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.feeding_rules import MIN_DO_MG_L, find_covering_window, find_qualifying_sample
from app.models.feed_event import FeedEvent
from app.models.pond import Pond
from app.models.user import User
from app.schemas.feed_event import FeedEventCreate, FeedEventOut

router = APIRouter(prefix="/api/feed-events", tags=["feed-events"])


@router.get("", response_model=List[FeedEventOut])
def list_events(
    pond_id: Optional[int] = Query(None, alias="pondId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(FeedEvent)
    if pond_id is not None:
        q = q.filter(FeedEvent.pond_id == pond_id)
    return q.order_by(FeedEvent.fed_at.desc()).all()


@router.post("", response_model=FeedEventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: FeedEventCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    pond = db.query(Pond).filter(Pond.id == payload.pond_id).first()
    if not pond:
        raise HTTPException(status_code=400, detail="塘口不存在")
    # 判定顺序固定：先窗口（409），后溶氧（400）
    if not find_covering_window(db, payload.pond_id, payload.fed_at):
        raise HTTPException(
            status_code=409, detail="投喂时刻不在该塘口任何启用的投喂窗口内，禁止投喂"
        )
    if not find_qualifying_sample(db, payload.pond_id, payload.fed_at):
        raise HTTPException(
            status_code=400,
            detail=f"投喂前6小时内无溶氧≥{MIN_DO_MG_L:g} mg/L的水质样，禁止投喂",
        )
    item = FeedEvent(
        pond_id=payload.pond_id,
        fed_at=payload.fed_at,
        feed_type=payload.feed_type,
        amount_kg=payload.amount_kg,
        operator_name=payload.operator_name,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(FeedEvent).filter(FeedEvent.id == event_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="投喂记录不存在")
    db.delete(item)
    db.commit()
