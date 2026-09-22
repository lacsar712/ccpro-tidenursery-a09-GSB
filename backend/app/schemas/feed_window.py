from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FeedWindowCreate(BaseModel):
    pond_id: int = Field(..., alias="pondId")
    start_at: datetime = Field(..., alias="startAt")
    end_at: datetime = Field(..., alias="endAt")
    enabled: bool = True

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("结束时刻必须晚于开始时刻")
        return self


class FeedWindowUpdate(BaseModel):
    pond_id: Optional[int] = Field(None, alias="pondId")
    start_at: Optional[datetime] = Field(None, alias="startAt")
    end_at: Optional[datetime] = Field(None, alias="endAt")
    enabled: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def check_range(self):
        if self.start_at is not None and self.end_at is not None:
            if self.end_at <= self.start_at:
                raise ValueError("结束时刻必须晚于开始时刻")
        return self


class FeedWindowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    pond_id: int = Field(serialization_alias="pondId")
    start_at: datetime = Field(serialization_alias="startAt")
    end_at: datetime = Field(serialization_alias="endAt")
    enabled: bool
