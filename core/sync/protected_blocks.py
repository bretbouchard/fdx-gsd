"""Protected block parsing and manipulation.

Handles the extraction and replacement of auto-generated content
within protected block markers in vault notes.

Protected block format:
    <!-- CONFUCIUS:BEGIN AUTO -->
    ... auto-generated content ...
    <!-- CONFUCIUS:END AUTO -->
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


# Marker constants for protected blocks
BEGIN_MARKER = "<!-- CONFUCIUS:BEGIN AUTO -->"
END_MARKER = "<!-- CONFUCIUS:END AUTO -->"

# Regex patterns for block detection
BEGIN_PATTERN = re.compile(r"<!--\s*CONFUCIUS:BEGIN\s+\w+\s*-->", re.IGNORECASE)
END_PATTERN = re.compile(r"<!--\s*CONFUCIUS:END\s+\w+\s*-->", re.IGNORECASE)


@dataclass
class ProtectedBlock:
    """Represents a protected block within a document."""

    start_marker: str
    end_marker: str
    content: str
    start_pos: int
    end_pos: int
    block_id: Optional[str] = None  # For future multi-block support


def extract_protected_content(
    text: str,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
) -> List[ProtectedBlock]:
    """
    Extract all protected blocks from text.

    Args:
        text: Document text to parse
        begin_marker: Start marker pattern (default: CONFUCIUS:BEGIN AUTO)
        end_marker: End marker pattern (default: CONFUCIUS:END AUTO)

    Returns:
        List of ProtectedBlock objects found in the text
    """
    blocks = []

    # Escape markers for regex
    begin_escaped = re.escape(begin_marker)
    end_escaped = re.escape(end_marker)

    # Pattern to match protected block with content
    pattern = re.compile(
        rf"({begin_escaped})(.*?)({end_escaped})",
        re.DOTALL,
    )

    for match in pattern.finditer(text):
        block = ProtectedBlock(
            start_marker=match.group(1),
            end_marker=match.group(3),
            content=match.group(2),
            start_pos=match.start(),
            end_pos=match.end(),
        )
        blocks.append(block)

    return blocks


def extract_protected_content_from_file(
    file_path: Path,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
) -> List[ProtectedBlock]:
    """
    Extract all protected blocks from a file.

    Args:
        file_path: Path to the file
        begin_marker: Start marker pattern
        end_marker: End marker pattern

    Returns:
        List of ProtectedBlock objects found in the file
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return []

    text = file_path.read_text(encoding="utf-8")
    return extract_protected_content(text, begin_marker, end_marker)


def replace_protected_content(
    text: str,
    new_content: str,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
    block_index: int = 0,
) -> str:
    """
    Replace content within a protected block.

    Args:
        text: Original document text
        new_content: New content to insert between markers
        begin_marker: Start marker pattern
        end_marker: End marker pattern
        block_index: Index of block to replace (default: 0, first block)

    Returns:
        Text with protected block content replaced

    Raises:
        ValueError: If specified block index doesn't exist
    """
    blocks = extract_protected_content(text, begin_marker, end_marker)

    if block_index >= len(blocks):
        raise ValueError(
            f"Block index {block_index} out of range. "
            f"Found {len(blocks)} protected blocks."
        )

    block = blocks[block_index]

    # Construct new block
    new_block = f"{block.start_marker}{new_content}{block.end_marker}"

    # Replace in text
    return text[:block.start_pos] + new_block + text[block.end_pos:]


def replace_protected_content_in_file(
    file_path: Path,
    new_content: str,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
    block_index: int = 0,
) -> bool:
    """
    Replace content within a protected block in a file.

    Args:
        file_path: Path to the file
        new_content: New content to insert between markers
        begin_marker: Start marker pattern
        end_marker: End marker pattern
        block_index: Index of block to replace

    Returns:
        True if replacement was made, False if file doesn't exist or no block found
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return False

    text = file_path.read_text(encoding="utf-8")

    try:
        new_text = replace_protected_content(
            text, new_content, begin_marker, end_marker, block_index
        )
        file_path.write_text(new_text, encoding="utf-8")
        return True
    except ValueError:
        return False


def has_protected_block(
    text: str,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
) -> bool:
    """
    Check if text contains a protected block.

    Args:
        text: Text to check
        begin_marker: Start marker pattern
        end_marker: End marker pattern

    Returns:
        True if protected block exists
    """
    blocks = extract_protected_content(text, begin_marker, end_marker)
    return len(blocks) > 0


def get_protected_content(
    text: str,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
    block_index: int = 0,
) -> Optional[str]:
    """
    Get content from a specific protected block.

    Args:
        text: Document text
        begin_marker: Start marker pattern
        end_marker: End marker pattern
        block_index: Index of block to get (default: 0)

    Returns:
        Content of the protected block, or None if not found
    """
    blocks = extract_protected_content(text, begin_marker, end_marker)

    if block_index >= len(blocks):
        return None

    return blocks[block_index].content


def split_at_protected_block(
    text: str,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
) -> Tuple[str, str, str]:
    """
    Split text into (before, protected_content, after) parts.

    Convenience function for working with a single protected block.

    Args:
        text: Document text
        begin_marker: Start marker pattern
        end_marker: End marker pattern

    Returns:
        Tuple of (before_markers, content_between_markers, after_markers)
        If no markers found, returns (text, "", "")
    """
    blocks = extract_protected_content(text, begin_marker, end_marker)

    if not blocks:
        return text, "", ""

    block = blocks[0]
    before = text[:block.start_pos]
    protected = block.content
    after = text[block.end_pos:]

    return before, protected, after


def append_to_protected_content(
    text: str,
    content_to_append: str,
    begin_marker: str = BEGIN_MARKER,
    end_marker: str = END_MARKER,
    block_index: int = 0,
) -> str:
    """
    Append content to an existing protected block.

    Args:
        text: Original document text
        content_to_append: Content to append to the protected block
        begin_marker: Start marker pattern
        end_marker: End marker pattern
        block_index: Index of block to modify

    Returns:
        Text with content appended to protected block

    Raises:
        ValueError: If specified block index doesn't exist
    """
    current_content = get_protected_content(text, begin_marker, end_marker, block_index)

    if current_content is None:
        raise ValueError(f"No protected block at index {block_index}")

    new_content = current_content + content_to_append
    return replace_protected_content(
        text, new_content, begin_marker, end_marker, block_index
    )


def wrap_in_protected_block(content: str, block_id: Optional[str] = None) -> str:
    """
    Wrap content in protected block markers.

    Args:
        content: Content to wrap
        block_id: Optional block identifier (future multi-block support)

    Returns:
        Content wrapped in protected block markers
    """
    # For now, use standard markers; block_id is reserved for future use
    return f"{BEGIN_MARKER}\n{content}\n{END_MARKER}"


def strip_protected_markers(text: str) -> str:
    """
    Remove protected block markers, keeping only the content.

    Args:
        text: Text with protected blocks

    Returns:
        Text with markers removed but content preserved
    """
    result = text

    # Replace markers with empty string (keeping content)
    result = re.sub(re.escape(BEGIN_MARKER) + r"\s*", "", result)
    result = re.sub(r"\s*" + re.escape(END_MARKER), "", result)

    return result


def ensure_markers(text: str, insert_at_end: bool = False) -> str:
    """
    Ensure text has protected block markers.

    If markers are missing, adds them. If markers exist, returns unchanged.

    Args:
        text: Text to check/modify
        insert_at_end: If True, append markers at end; otherwise insert before ## Notes

    Returns:
        Text with protected block markers
    """
    # Check if markers already exist
    if has_protected_block(text):
        return text

    # Look for ## Notes section to insert before it
    notes_pattern = r"(\n##\s+Notes)"
    match = re.search(notes_pattern, text)

    if match and not insert_at_end:
        # Insert before ## Notes section
        insert_pos = match.start()
        protected_block = f"\n{BEGIN_MARKER}\n{END_MARKER}\n"
        return text[:insert_pos] + protected_block + text[insert_pos:]
    else:
        # Append at end
        return f"{text.rstrip()}\n\n{BEGIN_MARKER}\n{END_MARKER}\n"
