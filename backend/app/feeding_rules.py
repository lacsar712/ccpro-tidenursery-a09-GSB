"""投喂判定规则（窗口 + 溶氧），投喂登记与塘口列表共用同一套核对逻辑。"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.feed_window import FeedWindow
from app.models.water_sample import WaterSample

# 溶氧阈值：投喂时刻前 6 小时内须有一条 do_mg_l >= 5 的水质样
DO_LOOKBACK_HOURS = 6
MIN_DO_MG_L = 5.0


def find_covering_window(db: Session, pond_id: int, at: datetime) -> Optional[FeedWindow]:
    """返回覆盖时刻 at 的启用投喂窗口（端点含），无则 None。"""
    return (
        db.query(FeedWindow)
        .filter(
            FeedWindow.pond_id == pond_id,
            FeedWindow.enabled.is_(True),
            FeedWindow.start_at <= at,
            FeedWindow.end_at >= at,
        )
        .order_by(FeedWindow.start_at)
        .first()
    )


def find_qualifying_sample(db: Session, pond_id: int, fed_at: datetime) -> Optional[WaterSample]:
    """返回投喂时刻前 6 小时内溶氧达标的水质样，无则 None。"""
    since = fed_at - timedelta(hours=DO_LOOKBACK_HOURS)
    return (
        db.query(WaterSample)
        .filter(
            WaterSample.pond_id == pond_id,
            WaterSample.sampled_at >= since,
            WaterSample.sampled_at <= fed_at,
            WaterSample.do_mg_l >= MIN_DO_MG_L,
        )
        .order_by(WaterSample.sampled_at.desc())
        .first()
    )


def has_window_overlap(
    db: Session, pond_id: int, start_at: datetime, end_at: datetime, exclude_id: Optional[int] = None
) -> bool:
    """同塘窗口区间相交（端点相接不算相交）。"""
    q = db.query(FeedWindow).filter(
        FeedWindow.pond_id == pond_id,
        FeedWindow.start_at < end_at,
        FeedWindow.end_at > start_at,
    )
    if exclude_id is not None:
        q = q.filter(FeedWindow.id != exclude_id)
    return db.query(q.exists()).scalar()
