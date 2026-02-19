"""Sync module - Round-trip editing support.

Provides change detection, protected block parsing, provenance
tracking, and conflict resolution for vault synchronization.
"""
from .change_detector import (
    ChangeDetector,
    ChangeRecord,
    FileState,
    calculate_file_hash,
)
from .conflict_resolver import (
    Conflict,
    ConflictResolver,
    ConflictStatus,
    ConflictTier,
)
from .protected_blocks import (
    BEGIN_MARKER,
    END_MARKER,
    ProtectedBlock,
    extract_protected_content,
    extract_protected_content_from_file,
    get_protected_content,
    has_protected_block,
    replace_protected_content,
    replace_protected_content_in_file,
    append_to_protected_content,
    wrap_in_protected_block,
    strip_protected_markers,
)
from .provenance import (
    ProvenanceRecord,
    ProvenanceTracker,
    SourceType,
)

__all__ = [
    # Change detection
    "ChangeDetector",
    "ChangeRecord",
    "FileState",
    "calculate_file_hash",
    # Conflict resolution
    "Conflict",
    "ConflictResolver",
    "ConflictStatus",
    "ConflictTier",
    # Protected blocks
    "BEGIN_MARKER",
    "END_MARKER",
    "ProtectedBlock",
    "extract_protected_content",
    "extract_protected_content_from_file",
    "get_protected_content",
    "has_protected_block",
    "replace_protected_content",
    "replace_protected_content_in_file",
    "append_to_protected_content",
    "wrap_in_protected_block",
    "strip_protected_markers",
    # Provenance
    "ProvenanceRecord",
    "ProvenanceTracker",
    "SourceType",
]
