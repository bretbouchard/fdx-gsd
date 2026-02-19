"""Data models for the media archive system.

Pydantic v2 models for:
- Work: A creative work (song, composition, script)
- Realization: A specific version (studio recording, demo)
- Performance: A live performance or take
- AliasRegistry: Global alias to canonical ID mapping
"""
from datetime import date as date_type
from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkMetadata(BaseModel):
    """Metadata for a creative work."""

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., description="Canonical title of the work")
    aliases: list[str] = Field(default_factory=list, description="Alternate titles")
    genre: Optional[str] = Field(None, description="Genre classification")
    year: Optional[int] = Field(None, description="Year of creation/release")
    isrc: Optional[str] = Field(None, description="ISRC code (for songs)")
    isbn: Optional[str] = Field(None, description="ISBN (for compositions)")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    notes: Optional[str] = Field(None, description="Additional notes")


class Work(BaseModel):
    """A creative work (song, composition, script, etc.)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique ID (format: work_{uuid8})")
    work_type: Literal["song", "composition", "script", "other"] = Field(
        "song", description="Type of work"
    )
    metadata: WorkMetadata = Field(..., description="Work metadata")
    realizations: list[str] = Field(default_factory=list, description="Realization IDs")
    performances: list[str] = Field(default_factory=list, description="Performance IDs")
    assets: list[str] = Field(default_factory=list, description="Asset file paths")


class RealizationMetadata(BaseModel):
    """Metadata for a realization (studio version, demo, remix)."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Realization name (e.g., 'Studio Version')")
    date: Optional[date_type] = Field(None, description="Realization date")
    studio: Optional[str] = Field(None, description="Studio name")
    engineer: Optional[str] = Field(None, description="Engineer name")
    producer: Optional[str] = Field(None, description="Producer name")
    version: Optional[str] = Field(None, description="Version identifier")
    notes: Optional[str] = Field(None, description="Additional notes")


class Realization(BaseModel):
    """A specific realization of a work (studio recording, demo, remix)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique ID (format: real_{uuid8})")
    work_id: str = Field(..., description="Parent work ID")
    metadata: RealizationMetadata = Field(..., description="Realization metadata")
    sessions: list[str] = Field(default_factory=list, description="DAW session file paths")
    stems: list[str] = Field(default_factory=list, description="Stem file paths")
    masters: list[str] = Field(default_factory=list, description="Master output paths")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class PerformanceMetadata(BaseModel):
    """Metadata for a live performance or take."""

    model_config = ConfigDict(from_attributes=True)

    date: date_type = Field(..., description="Performance date")
    venue: Optional[str] = Field(None, description="Venue name")
    city: Optional[str] = Field(None, description="City")
    personnel: list[str] = Field(default_factory=list, description="Performers and crew")
    setlist_position: Optional[int] = Field(None, description="Position in setlist")
    notes: Optional[str] = Field(None, description="Additional notes")


class Performance(BaseModel):
    """A live performance or take of a work."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique ID (format: perf_{uuid8})")
    work_id: str = Field(..., description="Parent work ID")
    metadata: PerformanceMetadata = Field(..., description="Performance metadata")
    audio: list[str] = Field(default_factory=list, description="Audio file paths")
    video: list[str] = Field(default_factory=list, description="Video file paths")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class AliasRegistry(BaseModel):
    """Global alias to canonical ID mapping."""

    model_config = ConfigDict(from_attributes=True)

    version: str = Field("1.0", description="Registry version")
    aliases: dict[str, str] = Field(
        default_factory=dict, description="Alias to canonical ID mapping"
    )
    conflicts: list[dict] = Field(
        default_factory=list, description="Ambiguous alias conflicts"
    )
