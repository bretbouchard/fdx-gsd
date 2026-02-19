"""ScriptGraph utilities.

Provides validation and loading utilities for ScriptGraph JSON data.
"""

import json
from pathlib import Path
from typing import Any, Dict

import jsonschema

# Schema location
SCHEMA_PATH = Path(__file__).parent / "schema.json"


def validate_scriptgraph(scriptgraph: Dict[str, Any]) -> bool:
    """
    Validate a ScriptGraph dict against the schema.

    Args:
        scriptgraph: ScriptGraph dictionary to validate

    Returns:
        True if valid

    Raises:
        jsonschema.ValidationError: If validation fails
    """
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    jsonschema.validate(scriptgraph, schema)
    return True


def load_scriptgraph(path: Path) -> Dict[str, Any]:
    """
    Load and validate a ScriptGraph JSON file.

    Args:
        path: Path to scriptgraph.json

    Returns:
        Validated ScriptGraph dictionary

    Raises:
        jsonschema.ValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_scriptgraph(data)
    return data


def create_empty_scriptgraph(project_id: str) -> Dict[str, Any]:
    """
    Create an empty but valid ScriptGraph.

    Args:
        project_id: Project identifier

    Returns:
        Minimal valid ScriptGraph dictionary
    """
    return {
        "version": "1.0",
        "project_id": project_id,
        "scenes": []
    }


__all__ = [
    "validate_scriptgraph",
    "load_scriptgraph",
    "create_empty_scriptgraph",
    "SCHEMA_PATH",
]
