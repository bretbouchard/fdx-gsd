#!/usr/bin/env python3
"""
Check that commit messages reference a REQ-ID when modifying code.

This ensures traceability between code changes and requirements.

Exemptions:
- Merge commits
- WIP commits
- Documentation-only changes
"""
import re
import sys
from pathlib import Path


def get_staged_files():
    """Get list of staged files."""
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip().split('\n') if result.stdout.strip() else []


def is_code_file(filepath):
    """Check if file is code (not docs)."""
    code_extensions = {'.py', '.js', '.ts', '.tsx', '.go', '.rs'}
    return Path(filepath).suffix in code_extensions


def check_commit_message(message_file):
    """Check commit message for REQ-ID."""
    with open(message_file) as f:
        message = f.read()

    # Exempt merge commits
    if message.startswith('Merge') or message.startswith('merge'):
        return True

    # Exempt WIP commits
    if 'WIP' in message or 'wip' in message:
        return True

    # Exempt if only docs changed
    staged = get_staged_files()
    if staged and not any(is_code_file(f) for f in staged):
        return True

    # Check for REQ-ID pattern
    req_pattern = r'REQ-[A-Z]{2,4}-\d+'
    if re.search(req_pattern, message):
        return True

    # Check for explicit "no-req" marker
    if 'no-req:' in message.lower():
        return True

    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: check_req_id.py <commit-msg-file>")
        sys.exit(1)

    message_file = sys.argv[1]

    if check_commit_message(message_file):
        sys.exit(0)

    print("""
❌ Commit message must reference a requirement ID.

Add a REQ-ID to your commit message, e.g.:
    Implement character extraction (CAN-01)

Or use 'no-req:' prefix for commits that don't affect requirements:
    no-req: Update README

See REQUIREMENTS.md for all REQ-IDs.
""")
    sys.exit(1)


if __name__ == "__main__":
    main()
