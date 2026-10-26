"""Structured outputs produced by the schedule stage."""

from datetime import datetime

from pydantic import BaseModel, Field


class ScheduledPost(BaseModel):
    post_text: str = Field(min_length=1, description="Final LinkedIn post text")
    publish_at: datetime = Field(
        description="ISO 8601 publication date and time with a UTC offset"
    )
    timezone: str = Field(min_length=1, description="IANA timezone for publication")
