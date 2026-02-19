# TOOLING ASSESSMENT: FDX GSD

**Purpose:** Identify ALL infrastructure/tooling needed to ensure proper tracking, accountability, and no surprises.

---

## What We HAVE ✅

### Project Management
| Tool | Status | Purpose |
|------|--------|---------|
| GSD (.planning/) | ✅ Active | Requirements, roadmap, state |
| Beads | ✅ Initialized | Task tracking |

### AI Infrastructure
| Tool | Status | Purpose |
|------|--------|---------|
| Confucius MCP | ✅ Available | Hierarchical memory |
| Council of Ricks | ✅ Available | Quality review |

### Development
| Tool | Status | Purpose |
|------|--------|---------|
| Git | ✅ Ready | Version control |
| Python 3.10+ | ✅ Available | Core language |

---

## What We NEED 🚧

### Phase 1 Specific

| Tool/Lib | Purpose | Options | Decision |
|----------|---------|---------|----------|
| **NER Library** | Entity extraction | spaCy, transformers, custom | ❓ NEEDED |
| **Fuzzy Matcher** | Alias resolution | rapidfuzz, thefuzz | ❓ NEEDED |
| **Test Fixtures** | Validation | Synthetic, public domain | ❓ NEEDED |

### Infrastructure Gaps

| Gap | Risk if Missing | Priority |
|-----|-----------------|----------|
| **No CI/CD** | Broken builds in main | HIGH |
| **No test framework** | Regressions undetected | HIGH |
| **No coverage tracking** | Unknown quality | MEDIUM |
| **No benchmark data** | Can't measure performance | MEDIUM |
| **No schema validation** | Invalid JSON accepted | MEDIUM |

---

## CRITICAL: What Would Cause "Not Tracking Shit" in 4 Months

### Scenario 1: Requirements Drift
**Problem:** Requirements change but REQUIREMENTS.md not updated
**Prevention:**
- [ ] Link every commit to REQ-ID
- [ ] Pre-commit hook checks REQ-ID in message
- [ ] Weekly audit: code vs requirements

### Scenario 2: Undetected Regressions
**Problem:** Feature works, later breaks, nobody notices
**Prevention:**
- [ ] Test suite with CI
- [ ] Coverage tracking >80%
- [ ] Automated FDX validation

### Scenario 3: Lost Context
**Problem:** Why was this decision made? Who knows.
**Prevention:**
- [ ] Confucius MCP stores all decisions
- [ ] STATE.md updated each session
- [ ] ADRs (Architecture Decision Records) for major choices

### Scenario 4: Untracked Work
**Problem:** Did work, but no bead, no commit message
**Prevention:**
- [ ] `/bret:sync` after every session
- [ ] Pre-commit hook requires bead ID OR explicit "no-bead"
- [ ] Weekly bead audit

### Scenario 5: Integration Assumptions
**Problem:** Built thing that doesn't work with other thing
**Prevention:**
- [ ] Integration tests for each phase boundary
- [ ] Contract tests for JSON schemas
- [ ] End-to-end test: ingest → export → validate

### Scenario 6: Performance Degradation
**Problem:** Works on small test, fails on real project
**Prevention:**
- [ ] Benchmark fixtures at multiple scales
- [ ] Performance CI gate
- [ ] Profile before/after each phase

---

## RECOMMENDED: Minimum Viable Infrastructure

### MUST HAVE Before Phase 1

1. **Test Framework** (pytest)
   ```
   tests/
     unit/
       test_fdx_writer.py
       test_entity_extraction.py
     integration/
       test_pipeline.py
     fixtures/
       sample_story_1.md
       expected_output.json
   ```

2. **CI Pipeline** (GitHub Actions)
   ```yaml
   # .github/workflows/ci.yml
   - Run tests
   - Check coverage
   - Validate JSON schemas
   - Lint (ruff, mypy)
   ```

3. **Pre-commit Hooks**
   ```yaml
   # .pre-commit-config.yaml
   - Check for REQ-ID in commits
   - Validate JSON schemas
   - Run linters
   ```

4. **Confucius Integration**
   ```
   - Store every decision
   - Store every pattern
   - Store every error/solution
   ```

### SHOULD HAVE Before Phase 1

5. **Bead Sync Script**
   - Creates beads for each requirement
   - Creates beads for each phase
   - Tracks REQ → Bead mapping

6. **ADR Template**
   - For NER choice
   - For fuzzy matcher choice
   - For threshold decisions

7. **Benchmark Suite**
   - Small story (10 inbox files)
   - Medium story (50 inbox files)
   - Large story (200 inbox files)

---

## Questions That Need Answers NOW

### Q1: NER Approach - Which One?

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **spaCy** | Fast, rule-based fallback, good docs | Less accurate than transformers | ? |
| **transformers** | State of art accuracy | Heavy, slow, GPU ideal | ? |
| **Custom regex** | Story-specific, lightweight | High maintenance, brittle | ? |
| **Hybrid** | Best of both | More complex | ? |

**Recommendation needed from user.**

### Q2: Test Data - Where From?

| Option | Pros | Cons |
|--------|------|------|
| Synthetic stories | Controlled, varied | May miss real patterns |
| Public domain scripts | Real screenplay structure | Copyright-adjacent |
| Personal notes | Real use case | Limited diversity |

**Recommendation needed from user.**

### Q3: Confidence Thresholds - What Values?

| Range | Action |
|-------|--------|
| >0.85 | Auto-accept |
| 0.50-0.85 | Queue for review |
| <0.50 | Auto-reject |

**Is this acceptable? Should it be configurable per project?**

### Q4: Confucius Integration - How?

| Option | Description |
|--------|-------------|
| A | Use Confucius MCP for ALL memory (decisions, patterns, errors) |
| B | Separate orchestration agent called "Confucius" + MCP for memory |
| C | Just use MCP, rename agent something else |

**Clarification needed.**

### Q5: What Else Is Missing?

Have I missed any critical infrastructure needs?

---

## Action Items

### Immediate (Before Any Phase 1 Work)
- [ ] Answer Q1-Q5 above
- [ ] Set up pytest framework
- [ ] Set up GitHub Actions CI
- [ ] Set up pre-commit hooks
- [ ] Create first test fixture
- [ ] Integrate Confucius MCP

### Before Phase 1 Complete
- [ ] Benchmark suite
- [ ] Coverage tracking
- [ ] ADR for NER choice
- [ ] Bead sync for requirements

---

## Checklist: "Will We Track Shit Properly?"

| Concern | Prevention | Status |
|---------|------------|--------|
| Requirements drift | REQ-ID in commits, weekly audit | ⬜ Not set up |
| Regressions | Test suite + CI | ⬜ Not set up |
| Lost context | Confucius MCP, STATE.md | ⬜ Partial |
| Untracked work | Beads, /bret:sync | ⬜ Partial |
| Integration failures | Contract tests | ⬜ Not set up |
| Performance issues | Benchmarks | ⬜ Not set up |

**Current Status: 2/6 prevention mechanisms in place**
**Target: 6/6 before Phase 1 starts**
