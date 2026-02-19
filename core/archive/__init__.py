"""Archive module - Media asset archive system.

Provides:
- Data models for works, realizations, performances
- Alias management with fuzzy search
- Registry for work tracking
- Index for searchable archive
"""
from .models import (
    Work,
    WorkMetadata,
    Realization,
    RealizationMetadata,
    Performance,
    PerformanceMetadata,
    AliasRegistry,
)

__all__ = [
    "Work",
    "WorkMetadata",
    "Realization",
    "RealizationMetadata",
    "Performance",
    "PerformanceMetadata",
    "AliasRegistry",
]
