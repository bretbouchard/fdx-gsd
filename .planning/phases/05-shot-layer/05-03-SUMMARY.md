# Phase 5 Wave 3 Summary: ShotSuggester Orchestrator

**Completed:** 2026-02-19
**Status:** ✅ Complete

## Deliverables

- [x] `core/shots/suggester.py` — ShotSuggester orchestrator class

## Implementation Details

### ShotSuggestionResult Dataclass

```python
@dataclass
class ShotSuggestionResult:
    success: bool
    scenes_processed: int = 0
    shots_suggested: int = 0
    errors: List[str] = field(default_factory=list)
```

### ShotSuggester Class

**Initialization:**
- Takes `build_path: Path` pointing to build directory
- Creates ShotDetector instance
- Loads scriptgraph.json on demand

**Key Methods:**

- `suggest() -> ShotSuggestionResult` — Main entry point, processes all scenes
- `_suggest_for_scene(scene) -> int` — Generates shots for a single scene
- `_add_shot(scene, shot_type, description, shot_order, **kwargs)` — Creates and adds shot
- `_create_shot_id(scene_number) -> str` — Generates unique shot IDs (shot_XXX_YYY)
- `get_shots() -> List[Shot]` — Returns sorted shots
- `get_shot_list() -> ShotList` — Returns ShotList for export
- `get_summary() -> Dict` — Returns statistics

**Scene Processing Logic:**

1. Always add establishing wide shot (WS) as first shot
2. Analyze each paragraph with ShotDetector
3. Track characters with dialogue
4. Add OTS shot if exactly 2 characters have dialogue
5. Proper shot numbering within each scene

**Shot ID Format:**
- `shot_XXX_YYY` where XXX = scene number, YYY = global counter

## Verification

```python
# Mock scriptgraph with 2 scenes
suggester = ShotSuggester(build_path)
result = suggester.suggest()

# Results:
# Success: True
# Scenes processed: 2
# Shots suggested: 7
# By type: WS=2, MS=2, CU=1, INSERT=1, OTS=1
# By scene: {1: 5, 2: 2}
```

## Commit

```
1649c06 feat(shots): Add ShotSuggester orchestrator (Phase 5 Wave 3)
```

## Next Steps

Wave 4: CLI integration + vault template update (05-04-PLAN.md)
