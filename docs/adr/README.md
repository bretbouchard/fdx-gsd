# Architecture Decision Records

This directory records significant architectural decisions for FDX GSD.

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| 0001 | Template | Template | - |
| 0002 | NER Approach - Interactive Disambiguation | ✅ Accepted | 2026-02-19 |
| 0003 | Fuzzy Matching - rapidfuzz | ✅ Accepted | 2026-02-19 |
| 0004 | Confidence Thresholds - Configurable | ✅ Accepted | 2026-02-19 |
| 0005 | Confucius Integration Architecture | ✅ Accepted | 2026-02-19 |

## Summary

All Phase 1 decisions resolved:

1. **NER** → No ML library. Lightweight extraction + interactive disambiguation. Always ask on ambiguity.
2. **Fuzzy Matching** → rapidfuzz for alias suggestions.
3. **Thresholds** → Configurable per project in gsd.yaml.
4. **Confucius** → MCP is the memory layer. Orchestration agent uses it for patterns/decisions.

## Test Data

Using **public domain screenplays** for test fixtures:
- Classic films with known character/location sets
- Validates extraction against known canon
- No copyright concerns
