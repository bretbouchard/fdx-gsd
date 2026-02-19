#!/usr/bin/env python3
"""
GSD CLI - Story Operating System Command Line Interface.

A Confucius-powered system for turning drunk drivel into polished screenplays.
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

import yaml


# Constants
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "project_template"
PROJECTS_DIR = Path(__file__).parent.parent.parent / "projects"


def generate_id(prefix: str) -> str:
    """Generate a unique ID with the given prefix."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}{short_uuid}"


def generate_evidence_id() -> str:
    """Generate an evidence block ID."""
    return f"ev_{uuid.uuid4().hex[:4]}"


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text


def load_config(project_path: Path) -> dict:
    """Load gsd.yaml configuration."""
    config_path = project_path / "gsd.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"No gsd.yaml found in {project_path}")

    with open(config_path) as f:
        return yaml.safe_load(f)


def save_config(project_path: Path, config: dict) -> None:
    """Save gsd.yaml configuration."""
    config_path = project_path / "gsd.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


# ============================================================================
# PHASE 0: Project Creation + Ingest
# ============================================================================

def cmd_new_project(args: argparse.Namespace) -> int:
    """
    Create a new GSD project.

    Usage: gsd new-project <project_name>
    """
    project_name = args.project_name
    project_path = PROJECTS_DIR / slugify(project_name)

    if project_path.exists() and not args.force:
        print(f"Error: Project '{project_name}' already exists at {project_path}")
        print("Use --force to overwrite")
        return 1

    # Create project directory
    if project_path.exists():
        shutil.rmtree(project_path)

    # Copy template
    shutil.copytree(TEMPLATE_DIR, project_path)

    # Update gsd.yaml with project info
    config = load_config(project_path)
    config["project"]["id"] = slugify(project_name)
    config["project"]["name"] = project_name
    config["project"]["created_at"] = datetime.now().isoformat()
    save_config(project_path, config)

    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=project_path, capture_output=True)

    # Initialize empty build files
    build_dir = project_path / "build"
    build_dir.mkdir(exist_ok=True)

    (build_dir / "evidence_index.json").write_text(json.dumps({
        "version": "1.0",
        "project_id": slugify(project_name),
        "evidence": {}
    }, indent=2))

    (build_dir / "disambiguation_queue.json").write_text(json.dumps({
        "version": "1.0",
        "project_id": slugify(project_name),
        "items": []
    }, indent=2))

    (build_dir / "storygraph.json").write_text(json.dumps({
        "version": "1.0",
        "project_id": slugify(project_name),
        "entities": [],
        "edges": [],
        "evidence_index": {}
    }, indent=2))

    (build_dir / "scriptgraph.json").write_text(json.dumps({
        "version": "1.0",
        "project_id": slugify(project_name),
        "scenes": []
    }, indent=2))

    # Remove template files that shouldn't be in new project
    template_files = [
        project_path / "vault" / "10_Characters" / "CHAR_Template.md",
        project_path / "vault" / "20_Locations" / "LOC_Template.md",
        project_path / "vault" / "50_Scenes" / "SCN_Template.md",
    ]
    for tf in template_files:
        if tf.exists():
            tf.unlink()

    print(f"✓ Created project: {project_name}")
    print(f"  Path: {project_path}")
    print(f"\nNext steps:")
    print(f"  cd {project_path}")
    print(f"  gsd ingest --text 'Your story notes here...'")

    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """
    Ingest raw material into the project.

    Usage:
      gsd ingest --text "..."
      gsd ingest inbox/notes.md
      gsd ingest inbox/*.md
    """
    # Find project root
    project_path = Path.cwd()
    while not (project_path / "gsd.yaml").exists():
        if project_path == project_path.parent:
            print("Error: Not in a GSD project. Run 'gsd new-project' first.")
            return 1
        project_path = project_path.parent

    config = load_config(project_path)
    inbox_dir = project_path / "inbox"
    inbox_dir.mkdir(exist_ok=True)
    build_dir = project_path / "build"

    # Load evidence index
    evidence_path = build_dir / "evidence_index.json"
    evidence_index = json.loads(evidence_path.read_text())

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if args.text:
        # Direct text input
        content = args.text

        # Generate filename
        filename = f"{timestamp}_001.md"
        inbox_file = inbox_dir / filename

        # Add block anchors to each paragraph
        lines = content.strip().split('\n')
        anchored_lines = []
        for line in lines:
            if line.strip():
                ev_id = generate_evidence_id()
                anchored_lines.append(f"{line} ^{ev_id}")

                # Register evidence
                evidence_index["evidence"][ev_id] = {
                    "source_path": f"inbox/{filename}",
                    "block_ref": f"^{ev_id}",
                    "text_excerpt": line.strip(),
                    "created_at": datetime.now().isoformat()
                }
            else:
                anchored_lines.append(line)

        # Write file
        inbox_file.write_text(f"# Raw Dump {timestamp}\n\n" + '\n'.join(anchored_lines))
        print(f"✓ Ingested text to: inbox/{filename}")

    elif args.files:
        # File input
        for file_pattern in args.files:
            for source_file in Path.cwd().glob(file_pattern):
                if source_file.suffix == '.md':
                    # Copy markdown files
                    content = source_file.read_text()
                    dest_file = inbox_dir / f"{timestamp}_{source_file.name}"

                    # Add block anchors if not present
                    lines = content.split('\n')
                    anchored_lines = []
                    for line in lines:
                        if line.strip() and not line.strip().endswith('^'):
                            # Check if already has block ref
                            import re
                            if not re.search(r'\^[a-z0-9]+$', line.strip()):
                                ev_id = generate_evidence_id()
                                anchored_lines.append(f"{line} ^{ev_id}")
                                evidence_index["evidence"][ev_id] = {
                                    "source_path": f"inbox/{dest_file.name}",
                                    "block_ref": f"^{ev_id}",
                                    "text_excerpt": line.strip(),
                                    "created_at": datetime.now().isoformat()
                                }
                            else:
                                anchored_lines.append(line)
                        else:
                            anchored_lines.append(line)

                    dest_file.write_text('\n'.join(anchored_lines))
                    print(f"✓ Ingested: {source_file} → inbox/{dest_file.name}")

    # Save evidence index
    evidence_path.write_text(json.dumps(evidence_index, indent=2))

    print(f"\nEvidence blocks: {len(evidence_index['evidence'])}")
    print(f"Next: gsd build canon")

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show project status."""
    project_path = Path.cwd()
    while not (project_path / "gsd.yaml").exists():
        if project_path == project_path.parent:
            print("Not in a GSD project.")
            return 1
        project_path = project_path.parent

    config = load_config(project_path)
    build_dir = project_path / "build"

    print(f"Project: {config['project']['name']}")
    print(f"ID: {config['project']['id']}")
    print(f"Created: {config['project']['created_at']}")
    print()

    # Count inbox items
    inbox_files = list((project_path / "inbox").glob("*.md"))
    print(f"Inbox: {len(inbox_files)} files")

    # Count vault entities
    vault = project_path / "vault"
    characters = len(list((vault / "10_Characters").glob("*.md")))
    locations = len(list((vault / "20_Locations").glob("*.md")))
    scenes = len(list((vault / "50_Scenes").glob("*.md")))
    print(f"Vault: {characters} characters, {locations} locations, {scenes} scenes")

    # Load build state
    if (build_dir / "evidence_index.json").exists():
        evidence = json.loads((build_dir / "evidence_index.json").read_text())
        print(f"Evidence: {len(evidence.get('evidence', {}))} blocks")

    if (build_dir / "disambiguation_queue.json").exists():
        queue = json.loads((build_dir / "disambiguation_queue.json").read_text())
        open_items = len([i for i in queue.get('items', []) if i['status'] == 'open'])
        print(f"Disambiguation queue: {open_items} open items")

    print()
    print("Pipeline phases enabled:")
    for phase in config['pipeline']['phases_enabled']:
        print(f"  • {phase}")

    return 0


# ============================================================================
# PHASE 1-2: Build Commands (Stubs)
# ============================================================================

def cmd_build(args: argparse.Namespace) -> int:
    """
    Build story artifacts.

    Usage:
      gsd build canon   # Extract canonical entities
      gsd build script  # Compose screenplay
    """
    what = args.what

    if what == "canon":
        print("Building canon... (Phase 1 - coming soon)")
        print("This will extract characters, locations, and scenes from inbox.")
        return 0

    elif what == "script":
        print("Building script... (Phase 2 - coming soon)")
        print("This will compose screenplay from storygraph.")
        return 0

    else:
        print(f"Unknown build target: {what}")
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """
    Export screenplay.

    Usage: gsd export fdx
    """
    project_path = Path.cwd()
    while not (project_path / "gsd.yaml").exists():
        if project_path == project_path.parent:
            print("Not in a GSD project.")
            return 1
        project_path = project_path.parent

    scriptgraph_path = project_path / "build" / "scriptgraph.json"
    if not scriptgraph_path.exists():
        print("Error: No scriptgraph.json found. Run 'gsd build script' first.")
        return 1

    exports_dir = project_path / "exports"
    exports_dir.mkdir(exist_ok=True)

    from core.exporters import write_fdx
    output_path = write_fdx(scriptgraph_path, exports_dir / "script.fdx")

    print(f"✓ Exported: {output_path}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    """
    Interactive disambiguation resolution.

    Usage: gsd resolve
    """
    print("Disambiguation resolution... (coming soon)")
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="gsd",
        description="GSD - Story Operating System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # new-project
    p_new = subparsers.add_parser("new-project", help="Create a new project")
    p_new.add_argument("project_name", help="Name of the project")
    p_new.add_argument("--force", "-f", action="store_true", help="Overwrite existing")
    p_new.set_defaults(func=cmd_new_project)

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest raw material")
    p_ingest.add_argument("--text", "-t", help="Text to ingest")
    p_ingest.add_argument("files", nargs="*", help="Files to ingest")
    p_ingest.set_defaults(func=cmd_ingest)

    # status
    p_status = subparsers.add_parser("status", help="Show project status")
    p_status.set_defaults(func=cmd_status)

    # build
    p_build = subparsers.add_parser("build", help="Build story artifacts")
    p_build.add_argument("what", choices=["canon", "script"], help="What to build")
    p_build.set_defaults(func=cmd_build)

    # export
    p_export = subparsers.add_parser("export", help="Export screenplay")
    p_export.add_argument("format", choices=["fdx"], default="fdx", help="Export format")
    p_export.set_defaults(func=cmd_export)

    # resolve
    p_resolve = subparsers.add_parser("resolve", help="Resolve disambiguations")
    p_resolve.set_defaults(func=cmd_resolve)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
