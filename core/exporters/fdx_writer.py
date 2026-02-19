"""
FDX Writer - Converts ScriptGraph to Final Draft XML format.

Minimal, durable implementation that produces valid .fdx files
compatible with Final Draft, Fade In, and WriterSolo.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# Mapping from internal paragraph types to FDX types
FDX_PARAGRAPH_MAP = {
    "scene_heading": "Scene Heading",
    "action": "Action",
    "character": "Character",
    "dialogue": "Dialogue",
    "parenthetical": "Parenthetical",
    "transition": "Transition",
    "shot": "Shot",
}


class FDXWriter:
    """Writes ScriptGraph to Final Draft XML format."""

    def __init__(self, scriptgraph: Dict[str, Any]):
        """Initialize with a ScriptGraph dictionary."""
        self.scriptgraph = scriptgraph
        self.project_id = scriptgraph.get("project_id", "unknown")

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "FDXWriter":
        """Load ScriptGraph from JSON file."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data)

    def _add_paragraph(
        self,
        content_el: ET.Element,
        p_type: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a paragraph element to the content."""
        fd_type = FDX_PARAGRAPH_MAP.get(p_type, "Action")
        p = ET.SubElement(content_el, "Paragraph", Type=fd_type)
        t = ET.SubElement(p, "Text")
        t.text = text

    def _build_xml(self) -> ET.ElementTree:
        """Build the FDX XML structure from ScriptGraph."""
        root = ET.Element(
            "FinalDraft",
            DocumentType="Script",
            Template="No",
            Version="1"
        )

        # Add metadata
        metadata = ET.SubElement(root, "Metadata")
        meta_info = self.scriptgraph.get("metadata", {})

        title = ET.SubElement(metadata, "Title")
        title.text = meta_info.get("title", self.project_id)

        # Add content
        content = ET.SubElement(root, "Content")

        scenes: List[Dict[str, Any]] = self.scriptgraph.get("scenes", [])
        scenes_sorted = sorted(scenes, key=lambda s: int(s.get("order", 999999)))

        for scene in scenes_sorted:
            paragraphs = scene.get("paragraphs", [])

            # Always start with scene heading
            slugline = scene.get("slugline", "")
            if slugline:
                self._add_paragraph(content, "scene_heading", slugline)

            for para in paragraphs:
                p_type = para.get("type", "action")
                text = para.get("text", "").strip()

                # Skip empty paragraphs and redundant scene headings
                if not text or (p_type == "scene_heading" and text == slugline):
                    continue

                self._add_paragraph(content, p_type, text, para.get("meta"))

            # Add blank line between scenes
            self._add_paragraph(content, "action", "")

        return ET.ElementTree(root)

    def write(self, out_path: Union[str, Path]) -> Path:
        """Write the FDX file to disk."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        tree = self._build_xml()
        tree.write(out_path, encoding="UTF-8", xml_declaration=True)

        return out_path

    def to_string(self) -> str:
        """Return FDX XML as string."""
        tree = self._build_xml()
        ET.indent(tree, space="  ")
        return ET.tostring(tree.getroot(), encoding="unicode", xml_declaration=True)


def write_fdx(
    scriptgraph_path: Union[str, Path],
    out_fdx_path: Union[str, Path]
) -> Path:
    """
    Convenience function to convert ScriptGraph JSON to FDX.

    Args:
        scriptgraph_path: Path to scriptgraph.json
        out_fdx_path: Output path for .fdx file

    Returns:
        Path to the written FDX file
    """
    writer = FDXWriter.from_file(scriptgraph_path)
    return writer.write(out_fdx_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python fdx_writer.py <scriptgraph.json> [output.fdx]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "exports/script.fdx"

    result = write_fdx(input_path, output_path)
    print(f"Written: {result}")
