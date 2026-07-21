from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApprovedIncident(BaseModel):
    """A report that has already passed a human review gate."""

    model_config = ConfigDict(str_strip_whitespace=True)

    incident_id: str = Field(min_length=3, max_length=120)
    title: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=800)
    location: str = Field(min_length=2, max_length=160)
    severity: Literal["low", "medium", "high", "critical"]
    language: Literal["English", "Amharic", "English + Amharic"] = (
        "English + Amharic"
    )
    audience: str = Field(default="Operations team", min_length=2, max_length=120)
    approved_by: str = Field(min_length=2, max_length=120)
    approved_at: datetime

    @field_validator("approved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("approved_at must include a timezone")
        return value


class BriefBundle(BaseModel):
    incident_id: str
    asset_path: Path
    manifest_path: Path
    bundle_path: Path
    asset_sha256: str
    manifest_hash: str
    manifest_verified: bool
    publication_status: Literal["awaiting_human_approval"] = (
        "awaiting_human_approval"
    )

