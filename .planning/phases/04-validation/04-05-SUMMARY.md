# Phase 4, Plan 05: KnowledgeValidator - COMPLETE

## Summary

Created KnowledgeValidator implementing KNOW-01/02/03/04 continuity rules:

1. **KnowledgeValidator Class** (`core/validation/knowledge_validator.py`)
   - Extends BaseValidator
   - INFORMATION_PATTERNS: Regex for reveals, discoveries, secrets
   - RELATIONSHIP_MARKERS: Patterns for friend, enemy, lover, betrayal, death
   - KNOWLEDGE_REFERENCE_PATTERNS: References to learned information

2. **Validation Rules**:
   - **KNOW-01**: Characters acting on unlearned info (ERROR)
     - Tracks knowledge states per character per scene
     - Flags references to unlearned facts
   - **KNOW-02**: Secret propagation issues (WARNING)
     - Tracks who knows secrets and when
     - Flags secret spread without shown channel
   - **KNOW-03**: Motive inconsistencies (WARNING)
     - Checks character actions against stated goals
   - **KNOW-04**: Relationship continuity issues (WARNING)
     - Detects abrupt relationship state changes
     - Flags suspicious transitions (friend->enemy, lover->betrayal)

3. **Implementation Details**:
   - `_build_knowledge_states()`: character_id -> {scene_num: set(facts)}
   - `_build_relationship_timeline()`: (char_a, char_b) -> [{relationship_changes}]
   - `_extract_revealed_information()`: Parses reveals/learns from content
   - `_is_clear_knowledge_violation()`: Reduces false positives

## Files Created

- `core/validation/knowledge_validator.py` (~450 lines)

## Verification

```bash
python -c "from core.validation import KnowledgeValidator, IssueCategory; print('OK')"
```
