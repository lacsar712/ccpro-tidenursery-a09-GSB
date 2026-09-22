from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FeedWindowCreate(BaseModel):
    pond_id: int = Field(..., alias="pondId")
    start_at: datetime = Field(..., alias="startAt")
    end_at: datetime = Field(..., alias="endAt")
    enabled: bool = True

    model_config = ConfigDict(populate_by_name=True)


class FeedWindowUpdate(BaseModel):
    pond_id: Optional[int] = Field(None, alias="pondId")
    start_at: Optional[datetime] = Field(None, alias="startAt")
    end_at: Optional[datetime] = Field(None, alias="endAt")
    enabled: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)


class FeedWindowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    start_at: datetime = Field(serialization_alias="startAt")
    end_at: datetime = Field(serialization_alias="endAt")
    enabled: bool
