from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LandingContentRead(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class LandingContentUpdate(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
