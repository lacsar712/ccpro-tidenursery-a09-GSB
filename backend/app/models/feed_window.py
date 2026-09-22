from datetime import datetime

from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FeedWindow(Base):
    __tablename__ = "feed_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pond_id: Mapped[int] = mapped_column(ForeignKey("ponds.id"), nullable=False, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    pond: Mapped["Pond"] = relationship("Pond", back_populates="feed_windows")
