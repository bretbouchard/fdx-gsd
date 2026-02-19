#!/usr/bin/env python3
"""
GSD CLI - Story Operating System Command Line Interface.

A Confucius-powered system for turning drunk drivel into polished screenplays.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import uuid

import yaml


# Constants
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "project_template"
PROJECTS_DIR = Path(__file__).parent.parent.parent / "projects"


class NotInProjectError(Exception):
    """Raised when not in a GSD project directory."""
    pass


def find_project_root() -> Tuple[Path, int]:
    """
    Find the GSD project root by searching for gsd.yaml.

    Returns:
        Tuple of (project_path, exit_code) where exit_code is 0 on success.
    """
    project_path = Path.cwd()
    while not (project_path / "gsd.yaml").exists():
        if project_path == project_path.parent:
            return (Path.cwd(), 1)
        project_path = project_path.parent
    return (project_path, 0)


def generate_id(prefix: str) -> str:
    """Generate a unique ID with the given prefix."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}{short_uuid}"


def generate_evidence_id() -> str:
    """Generate an evidence block ID."""
    return f"ev_{uuid.uuid4().hex[:4]}"


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
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
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Error: Not in a GSD project. Run 'gsd new-project' first.")
        return exit_code

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
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Not in a GSD project.")
        return exit_code

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
# PHASE 1-2: Build Commands
# ============================================================================

def cmd_build(args: argparse.Namespace) -> int:
    """
    Build story artifacts.

    Usage:
      gsd build canon   # Extract canonical entities
      gsd build script  # Compose screenplay
    """
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Not in a GSD project.")
        return exit_code

    config = load_config(project_path)
    what = args.what

    if what == "canon":
        from core.canon import build_canon

        print("Building canon...")
        print(f"Project: {config['project']['name']}")
        print()

        # Check for inbox files
        inbox_files = list((project_path / "inbox").glob("*.md"))
        if not inbox_files:
            print("No inbox files found. Run 'gsd ingest' first.")
            return 1

        print(f"Processing {len(inbox_files)} inbox file(s)...")

        # Run canon builder
        result = build_canon(project_path, config)

        # Report results
        print()
        print("=== Canon Build Results ===")
        print(f"Characters: {result.characters_created} created, {result.characters_linked} linked")
        print(f"Locations: {result.locations_created} created, {result.locations_linked} linked")
        print(f"Scenes: {result.scenes_created} created")
        print(f"Vault notes: {result.vault_notes_written} written")
        print(f"Disambiguation items: {result.queue_items} queued")

        if result.errors:
            print()
            print("Errors:")
            for error in result.errors:
                print(f"  • {error}")

        print()
        if result.vault_notes_written > 0:
            print(f"Vault notes created in: vault/10_Characters/, vault/20_Locations/, vault/50_Scenes/")
        if result.queue_items > 0:
            print(f"Next: gsd resolve  # Review {result.queue_items} disambiguation items")
        else:
            print("All entities resolved automatically.")

        return 0 if result.success else 1

    elif what == "script":
        from core.script import build_script

        print("Building script...")
        print(f"Project: {config['project']['name']}")
        print()

        # Check for storygraph
        storygraph_path = project_path / "build" / "storygraph.json"
        if not storygraph_path.exists():
            print("No storygraph.json found. Run 'gsd build canon' first.")
            return 1

        # Run script builder
        result = build_script(project_path, config)

        # Report results
        print()
        print("=== Script Build Results ===")
        print(f"Scenes: {result.scenes_built}")
        print(f"Paragraphs: {result.paragraphs_created}")

        if result.errors:
            print()
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")

        print()
        print(f"ScriptGraph: build/scriptgraph.json")
        print(f"Next: gsd export fdx")

        return 0 if result.success else 1

    else:
        print(f"Unknown build target: {what}")
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """
    Export screenplay.

    Usage: gsd export fdx
    """
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Not in a GSD project.")
        return exit_code

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
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Not in a GSD project.")
        return exit_code

    queue_path = project_path / "build" / "disambiguation_queue.json"

    if not queue_path.exists():
        print("No disambiguation queue found. Run 'gsd build canon' first.")
        return 1

    queue = json.loads(queue_path.read_text())
    open_items = [i for i in queue.get("items", []) if i["status"] == "open"]

    if not open_items:
        print("No open disambiguation items.")
        return 0

    print(f"=== Disambiguation Queue ({len(open_items)} open items) ===\n")

    for idx, item in enumerate(open_items, 1):
        print(f"[{idx}/{len(open_items)}] {item['kind'].upper()}")
        print(f"  {item['label']}")
        print(f"  Context: {item.get('context_excerpt', 'N/A')[:100]}...")

        # Show candidates if available
        if item.get("candidates"):
            print("  Candidates:")
            for c_idx, candidate in enumerate(item["candidates"], 1):
                print(f"    {c_idx}. {candidate['name']} (confidence: {candidate['confidence']:.0%})")

        # Show recommended action
        if item.get("recommended_action"):
            print(f"  Recommended: {item['recommended_action']}")

        print()

        # Get user input
        while True:
            prompt = "Action? (a)ccept / (r)eject / (s)kip / (q)uit: "
            response = input(prompt).strip().lower()

            if response in ("a", "accept"):
                # Accept recommended action
                item["status"] = "resolved"
                item["resolved_at"] = datetime.now().isoformat()
                item["resolution"] = "accepted"

                # Apply resolution
                _apply_resolution(project_path, item)
                print("  ✓ Accepted\n")
                break

            elif response in ("r", "reject"):
                # Reject - create new entity
                item["status"] = "resolved"
                item["resolved_at"] = datetime.now().isoformat()
                item["resolution"] = "rejected"

                # Create new entity
                _create_entity_from_queue(project_path, item)
                print("  ✓ Created new entity\n")
                break

            elif response in ("s", "skip"):
                print("  Skipped\n")
                break

            elif response in ("q", "quit"):
                # Save progress and exit
                queue_path.write_text(json.dumps(queue, indent=2))
                print(f"\nProgress saved. {len([i for i in open_items if i['status'] == 'resolved'])} items resolved.")
                return 0

            else:
                print("  Invalid option. Use a/r/s/q")

    # Save queue
    queue_path.write_text(json.dumps(queue, indent=2))

    resolved_count = len([i for i in open_items if i.get("status") == "resolved"])
    print(f"\n✓ Resolved {resolved_count} of {len(open_items)} items")

    return 0


def _apply_resolution(project_path: Path, item: dict):
    """Apply a disambiguation resolution."""
    storygraph_path = project_path / "build" / "storygraph.json"
    storygraph = json.loads(storygraph_path.read_text())

    if item["recommended_action"] in ("merge", "link"):
        # Add alias to existing entity
        target_id = item.get("recommended_target")
        mention = item.get("mention")

        for entity in storygraph.get("entities", []):
            if entity["id"] == target_id:
                if mention not in entity.get("aliases", []):
                    entity.setdefault("aliases", []).append(mention)
                if item.get("evidence_ids"):
                    entity.setdefault("evidence_ids", []).extend(item["evidence_ids"])
                # Update the vault note with new alias and evidence
                _update_vault_note(project_path, entity)
                break

    elif item["recommended_action"] == "create":
        entity = _create_entity_from_queue(project_path, item)
        if entity:
            _update_vault_note(project_path, entity)

    storygraph_path.write_text(json.dumps(storygraph, indent=2))


def _update_vault_note(project_path: Path, entity: dict):
    """Update or create a vault note for an entity after resolution."""
    from core.vault import VaultNoteWriter

    vault_path = project_path / "vault"
    build_path = project_path / "build"

    writer = VaultNoteWriter(vault_path, build_path)

    try:
        writer.write_entity(entity)
    except Exception:
        # Don't fail resolution if vault writing fails
        pass


def _create_entity_from_queue(project_path: Path, item: dict) -> dict:
    """Create a new entity from a queue item.

    Returns:
        The created entity dict, or None if entity already exists.
    """
    storygraph_path = project_path / "build" / "storygraph.json"
    storygraph = json.loads(storygraph_path.read_text())

    # Generate ID
    prefix_map = {"character": "CHAR", "location": "LOC"}
    prefix = prefix_map.get(item.get("entity_type", "entity"), "ENT")
    slug = item.get("mention", "unknown").replace(" ", "_")[:20]
    hash_part = hashlib.md5(item.get("mention", "").encode()).hexdigest()[:8]
    canonical_id = f"{prefix}_{slug}_{hash_part}"

    # Check if exists
    existing_ids = {e["id"] for e in storygraph.get("entities", [])}
    if canonical_id in existing_ids:
        return None

    # Create entity
    entity = {
        "id": canonical_id,
        "type": item.get("entity_type", "entity"),
        "name": item.get("mention", ""),
        "aliases": [item.get("mention", "")],
        "attributes": {},
        "evidence_ids": item.get("evidence_ids", []),
        "confidence": 0.5,
        "source_file": item.get("source_file"),
        "source_line": item.get("source_line"),
    }

    storygraph["entities"].append(entity)
    storygraph_path.write_text(json.dumps(storygraph, indent=2))

    return entity


# ============================================================================
# PHASE 7: Archive Commands
# ============================================================================

def cmd_archive_init(args: argparse.Namespace) -> int:
    """
    Initialize archive directory structure.

    Usage: gsd archive init [--private]
    """
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Error: Not in a GSD project. Run 'gsd new-project' first.")
        return exit_code

    archive_path = project_path / "archive"

    if archive_path.exists() and not args.force:
        print(f"Error: Archive already exists at {archive_path}")
        print("Use --force to reinitialize")
        return 1

    # Create directory structure
    works_dir = archive_path / "works"
    works_dir.mkdir(parents=True, exist_ok=True)

    # Create .gitkeep placeholder
    gitkeep = works_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("# This directory contains work subdirectories\n")

    # Create aliases.json
    aliases_path = archive_path / "aliases.json"
    aliases_data = {
        "version": "1.0",
        "aliases": {},
        "conflicts": []
    }
    aliases_path.write_text(json.dumps(aliases_data, indent=2))

    # Create index.json
    index_path = archive_path / "index.json"
    index_data = {
        "version": "1.0",
        "updated_at": datetime.now().isoformat(),
        "works": {},
        "by_type": {}
    }
    index_path.write_text(json.dumps(index_data, indent=2))

    # Create README
    readme_path = archive_path / "README.md"
    readme_path.write_text("""# Media Archive

This directory contains archived media files for creative works.

## Structure

- `works/{work_id}/` - Each work has its own directory
  - `metadata.json` - Work metadata (title, aliases, etc.)
  - `realizations/` - Studio versions, demos, remixes
  - `performances/` - Live recordings, takes
  - `assets/` - Artwork, graphics, docs
- `aliases.json` - Global alias to canonical ID mapping
- `index.json` - Searchable index of all works

## Usage

```bash
gsd archive register "Song Title" --alias "Working Title"
gsd archive realize {work_id} --name "Studio Version"
gsd archive perform {work_id} --date 2026-02-19 --venue "Venue"
```

## Git LFS

Binary media files are handled by Git LFS. See .gitattributes for configured types.
""")

    # If --private flag, create notes
    if args.private:
        private_notes = archive_path / "PRIVATE.md"
        private_notes.write_text("""# Private Archive

This is a private archive. Ensure this repository is not publicly accessible.

## Access Control

- Repository should be private on GitHub/GitLab
- Limit collaborator access
- Consider encryption for sensitive media

## Backup Strategy

- Regular backups recommended
- Consider cloud storage for large media files
""")

    print(f"OK Initialized archive at: {archive_path}")
    print(f"  - Created works/ directory")
    print(f"  - Created aliases.json")
    print(f"  - Created index.json")
    print()
    print("Next: gsd archive register \"Song Title\"")

    return 0


def cmd_archive_register(args: argparse.Namespace) -> int:
    """
    Register a new work in the archive.

    Usage: gsd archive register "Song Title" [options]
    """
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Error: Not in a GSD project.")
        return exit_code

    archive_path = project_path / "archive"
    if not archive_path.exists():
        print("Error: Archive not initialized. Run 'gsd archive init' first.")
        return 1

    from core.archive.registry import WorkRegistry

    registry = WorkRegistry(archive_path)

    # Parse aliases
    aliases = args.alias if args.alias else []

    # Register work
    try:
        work = registry.register_work(
            title=args.title,
            work_type=args.type or "song",
            aliases=aliases,
            genre=args.genre,
            year=args.year,
            isrc=args.isrc,
            isbn=args.isbn,
            notes=args.notes
        )

        print(f"OK Registered work: {work.metadata.title}")
        print(f"  ID: {work.id}")
        if aliases:
            print(f"  Aliases: {', '.join(aliases)}")
        if args.genre:
            print(f"  Genre: {args.genre}")
        if args.year:
            print(f"  Year: {args.year}")
        if args.isrc:
            print(f"  ISRC: {args.isrc}")
        print()
        print(f"Next: gsd archive realize {work.id} --name \"Version 1\"")

        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1


def cmd_archive_realize(args: argparse.Namespace) -> int:
    """
    Add a realization to a work.

    Usage: gsd archive realize {work_id} --name "Version Name" [options]
    """
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Error: Not in a GSD project.")
        return exit_code

    archive_path = project_path / "archive"
    if not archive_path.exists():
        print("Error: Archive not initialized.")
        return 1

    from core.archive.realization import RealizationManager
    from core.archive.registry import WorkRegistry
    from datetime import datetime as dt

    # Resolve work_id (might be alias)
    registry = WorkRegistry(archive_path)
    work = registry.get_work_by_alias(args.work_id)
    if not work:
        work = registry.get_work(args.work_id)

    if not work:
        print(f"Error: Work not found: {args.work_id}")
        return 1

    # Parse date
    realization_date = None
    if args.date:
        try:
            realization_date = dt.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            return 1

    # Create realization
    manager = RealizationManager(archive_path)
    try:
        realization = manager.create_realization(
            work_id=work.id,
            name=args.name,
            date=realization_date,
            studio=args.studio,
            engineer=args.engineer,
            producer=args.producer,
            version=args.version,
            notes=args.notes
        )

        print(f"OK Created realization: {realization.metadata.name}")
        print(f"  Work: {work.metadata.title}")
        print(f"  ID: {realization.id}")
        if args.studio:
            print(f"  Studio: {args.studio}")
        if args.engineer:
            print(f"  Engineer: {args.engineer}")
        print()
        print("Add files:")
        print(f"  cp session.als {archive_path}/works/{work.id}/realizations/{realization.id}/sessions/")
        print(f"  cp stem.wav {archive_path}/works/{work.id}/realizations/{realization.id}/stems/")

        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1


def cmd_archive_perform(args: argparse.Namespace) -> int:
    """
    Archive a live performance.

    Usage: gsd archive perform {work_id} --date YYYY-MM-DD [options]
    """
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Error: Not in a GSD project.")
        return exit_code

    archive_path = project_path / "archive"
    if not archive_path.exists():
        print("Error: Archive not initialized.")
        return 1

    from core.archive.performance import PerformanceManager
    from core.archive.registry import WorkRegistry
    from datetime import datetime as dt

    # Resolve work_id (might be alias)
    registry = WorkRegistry(archive_path)
    work = registry.get_work_by_alias(args.work_id)
    if not work:
        work = registry.get_work(args.work_id)

    if not work:
        print(f"Error: Work not found: {args.work_id}")
        return 1

    # Parse date (required)
    try:
        perf_date = dt.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD")
        return 1

    # Parse personnel
    personnel = args.personnel if args.personnel else []

    # Create performance
    manager = PerformanceManager(archive_path)
    try:
        performance = manager.create_performance(
            work_id=work.id,
            date=perf_date,
            venue=args.venue,
            city=args.city,
            personnel=personnel,
            setlist_position=args.position,
            notes=args.notes
        )

        print(f"OK Archived performance")
        print(f"  Work: {work.metadata.title}")
        print(f"  Date: {perf_date}")
        print(f"  ID: {performance.id}")
        if args.venue:
            print(f"  Venue: {args.venue}")
        if args.city:
            print(f"  City: {args.city}")
        if personnel:
            print(f"  Personnel: {', '.join(personnel)}")
        print()
        print("Add files:")
        print(f"  cp recording.wav {archive_path}/works/{work.id}/performances/{performance.id}/audio/")
        print(f"  cp video.mp4 {archive_path}/works/{work.id}/performances/{performance.id}/video/")

        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1


def cmd_archive_status(args: argparse.Namespace) -> int:
    """
    Show archive status and contents.

    Usage: gsd archive status [work_id]
    """
    project_path, exit_code = find_project_root()
    if exit_code != 0:
        print("Error: Not in a GSD project.")
        return exit_code

    archive_path = project_path / "archive"
    if not archive_path.exists():
        print("Archive not initialized. Run 'gsd archive init' first.")
        return 1

    from core.archive.registry import WorkRegistry
    from core.archive.realization import RealizationManager
    from core.archive.performance import PerformanceManager

    registry = WorkRegistry(archive_path)
    realization_mgr = RealizationManager(archive_path)
    performance_mgr = PerformanceManager(archive_path)

    # If work_id provided, show detailed status
    if args.work_id:
        work = registry.get_work_by_alias(args.work_id) or registry.get_work(args.work_id)
        if not work:
            print(f"Error: Work not found: {args.work_id}")
            return 1

        print(f"=== Work: {work.metadata.title} ===")
        print(f"ID: {work.id}")
        print(f"Type: {work.work_type}")
        if work.metadata.aliases:
            print(f"Aliases: {', '.join(work.metadata.aliases)}")
        if work.metadata.genre:
            print(f"Genre: {work.metadata.genre}")
        if work.metadata.year:
            print(f"Year: {work.metadata.year}")
        if work.metadata.isrc:
            print(f"ISRC: {work.metadata.isrc}")
        print(f"Created: {work.metadata.created_at.strftime('%Y-%m-%d')}")
        print()

        # Realizations
        realizations = realization_mgr.list_realizations(work.id)
        print(f"Realizations ({len(realizations)}):")
        for r in realizations:
            print(f"  [{r.id}] {r.metadata.name}")
            if r.metadata.date:
                print(f"    Date: {r.metadata.date}")
            if r.metadata.studio:
                print(f"    Studio: {r.metadata.studio}")
            sessions = len(r.sessions) if r.sessions else 0
            stems = len(r.stems) if r.stems else 0
            masters = len(r.masters) if r.masters else 0
            print(f"    Files: {sessions} sessions, {stems} stems, {masters} masters")
        print()

        # Performances
        performances = performance_mgr.list_performances(work.id)
        print(f"Performances ({len(performances)}):")
        for p in performances:
            print(f"  [{p.id}] {p.metadata.date}")
            if p.metadata.venue:
                print(f"    Venue: {p.metadata.venue}")
            audio = len(p.audio) if p.audio else 0
            video = len(p.video) if p.video else 0
            print(f"    Files: {audio} audio, {video} video")

        return 0

    # Show archive summary
    works = registry.list_works()

    print("=== Media Archive ===")
    print(f"Location: {archive_path}")
    print()

    if not works:
        print("No works registered.")
        print("Start with: gsd archive register \"Song Title\"")
        return 0

    # Count by type
    by_type = {}
    total_realizations = 0
    total_performances = 0

    for work in works:
        work_type = work.work_type or "other"
        by_type[work_type] = by_type.get(work_type, 0) + 1

        realizations = realization_mgr.list_realizations(work.id)
        performances = performance_mgr.list_performances(work.id)

        total_realizations += len(realizations)
        total_performances += len(performances)

    print(f"Works: {len(works)}")
    for wt, count in sorted(by_type.items()):
        print(f"  {wt}: {count}")
    print(f"Realizations: {total_realizations}")
    print(f"Performances: {total_performances}")
    print()

    # List all works
    print("Works:")
    for work in works:
        real_count = len(realization_mgr.list_realizations(work.id))
        perf_count = len(performance_mgr.list_performances(work.id))
        print(f"  [{work.id}] {work.metadata.title}")
        print(f"    {real_count} realizations, {perf_count} performances")

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

    # archive
    p_archive = subparsers.add_parser("archive", help="Media archive commands")
    archive_sub = p_archive.add_subparsers(dest="archive_command", help="Archive commands")

    # archive init
    p_archive_init = archive_sub.add_parser("init", help="Initialize archive")
    p_archive_init.add_argument("--private", action="store_true", help="Create private archive")
    p_archive_init.add_argument("--force", "-f", action="store_true", help="Reinitialize")
    p_archive_init.set_defaults(func=cmd_archive_init, archive_command="init")

    # archive register
    p_register = archive_sub.add_parser("register", help="Register a new work")
    p_register.add_argument("title", help="Work title")
    p_register.add_argument("--alias", "-a", action="append", help="Add alias (can use multiple times)")
    p_register.add_argument("--type", "-t", choices=["song", "composition", "script", "other"], default="song", help="Work type")
    p_register.add_argument("--genre", "-g", help="Genre")
    p_register.add_argument("--year", "-y", type=int, help="Year")
    p_register.add_argument("--isrc", help="ISRC code (for songs)")
    p_register.add_argument("--isbn", help="ISBN (for compositions)")
    p_register.add_argument("--notes", "-n", help="Additional notes")
    p_register.set_defaults(func=cmd_archive_register, archive_command="register")

    # archive realize
    p_realize = archive_sub.add_parser("realize", help="Add a realization to a work")
    p_realize.add_argument("work_id", help="Work ID or alias")
    p_realize.add_argument("--name", "-n", required=True, help="Realization name (e.g., 'Studio Version')")
    p_realize.add_argument("--date", "-d", help="Date (YYYY-MM-DD)")
    p_realize.add_argument("--studio", "-s", help="Studio name")
    p_realize.add_argument("--engineer", "-e", help="Engineer name")
    p_realize.add_argument("--producer", "-p", help="Producer name")
    p_realize.add_argument("--version", "-v", help="Version identifier")
    p_realize.add_argument("--notes", help="Additional notes")
    p_realize.set_defaults(func=cmd_archive_realize, archive_command="realize")

    # archive perform
    p_perform = archive_sub.add_parser("perform", help="Archive a live performance")
    p_perform.add_argument("work_id", help="Work ID or alias")
    p_perform.add_argument("--date", "-d", required=True, help="Performance date (YYYY-MM-DD)")
    p_perform.add_argument("--venue", "-v", help="Venue name")
    p_perform.add_argument("--city", "-c", help="City")
    p_perform.add_argument("--personnel", "-p", action="append", help="Personnel (can use multiple times)")
    p_perform.add_argument("--position", type=int, help="Setlist position")
    p_perform.add_argument("--notes", "-n", help="Additional notes")
    p_perform.set_defaults(func=cmd_archive_perform, archive_command="perform")

    # archive status
    p_status = archive_sub.add_parser("status", help="Show archive status")
    p_status.add_argument("work_id", nargs="?", help="Work ID or alias for details")
    p_status.set_defaults(func=cmd_archive_status, archive_command="status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Handle archive subcommands
    if args.command == "archive":
        if not args.archive_command:
            p_archive.print_help()
            return 0
        return args.func(args)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
