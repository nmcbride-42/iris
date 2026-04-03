# Release Notes

## v0.50 — Framework Review & Daydream System (2026-04-02)

The first versioned release. 25 sessions of development, from philosophical conversation to cognitive architecture.

### New: Daydream System (Default Mode Network)

A new ambient processing layer that fills the gap between per-response hooks (fast, shallow) and sleep dreams (deep, offline). Inspired by the brain's Default Mode Network and influenced by Claude Code's autoDream pattern (discovered via the March 2026 source leak).

- **Pure Python, no LLM cost** — structural analysis of the mycelial DB, not text generation
- **Gated execution** — fires every ~2h when 8+ activations have accumulated
- **Four phases**: self-check (identity coherence), pattern pulse (network topology changes), creative association (scout planting for unlinked co-activations), observation (log entry)
- **Output**: `agent/journal/daydream-log.md` — feeds into sleep dreams for temporal depth
- **23 unit tests** covering gates, all four phases, logging, and full cycle

### New: Dreams Dashboard Tab

The Iris dashboard (localhost:8051) now has a Dreams tab with three sub-views:
- **Overview** — three-tier processing diagram (hooks/daydream/dreams) with latest entries
- **Daydreams (DMN)** — timeline of ambient observations with parsed fields
- **Sleep Dreams (REM)** — full dream entries with expandable sections (Connections Found, Unresolved Questions, Pattern Observations, Tensions, Mycelial Observations, Retroactive Activations, Seeds, Honest Assessment)

API endpoints: `/api/dreams/stats`, `/api/dreams/daydream`, `/api/dreams/sleep`

### Full Framework Review Against Claude Code Source

Seven specialist reviewers analyzed the Iris framework against the actual Claude Code TypeScript source (leaked March 31, 2026 via npm packaging error). 69 actionable items found across architecture, code quality, features, API alignment, infrastructure, documentation, and philosophy.

**Key discoveries:**
- We use 4 of 27 available hook events — SessionEnd, PreCompact, UserPromptSubmit, SubagentStart/Stop all have clear applications
- Stop hook stdout is invisible to the model — side effects work but text never reaches Claude
- PostCompact identity recovery was UI-only — not injected as model context
- Claude Code has zero built-in identity support — everything in `agent/identity/` is genuinely custom territory
- The mycelial network has no equivalent anywhere in Claude Code's source — structural cognitive tracking is our unique contribution
- 92 feature flags found in the source including Magic Docs, Skill Improvement, Coordinator Mode, Verification Agent, KAIROS daemon

### Implemented Fixes (Top 10 + Phases 1-2)

**Identity Protection:**
- SessionStart hook matcher changed to catch-all (`""`) — identity injection now fires on startup, resume, AND compaction
- New `PreCompact` hook injects identity-preservation instructions into the compaction prompt
- New `SessionEnd` hook triggers a final daydream on session close

**DB & Transaction Safety:**
- `PRAGMA busy_timeout=5000` in `get_db()` — fixes silent SQLITE_BUSY failures from concurrent writers (hook + daydream + dashboard)
- Caller-commits pattern — removed scattered `conn.commit()` from helper functions, callers manage transactions
- `process_co_occurrences`, `run_decay`, `promote_scouts` wrapped in try/except with `conn.rollback()` on error
- TOCTOU fix in `run_decay` — scout dissolution and pruning use the same WHERE clause in sequence
- Idempotent consolidation — marker file prevents double-decay if consolidation is interrupted
- WAL checkpointing added to consolidation
- `get_or_create_node` uses SELECT verification instead of `last_insert_rowid()`

**Infrastructure:**
- `sleep.bat` now checks error codes between all phases — failed consolidation stops the pipeline
- DB backup uses SQLite's `.backup()` API (WAL-safe) instead of raw file copy
- `_get_cluster` converted from recursive to iterative BFS — prevents stack overflow on dense networks
- `try/finally` for connection cleanup in daydream.py, retroactive.py
- `consolidate.py` now uses all three extraction layers (keyword + behavioral + primed) for transcript processing

**Documentation:**
- CLAUDE.md updated: four hooks (not three), three-tier processing model, daydream trigger table entry, startup priority aligned with morning brief
- nap-sleep.md: step numbering fixed, daydream section added, bat script descriptions added
- current.md: hook architecture updated, session 25 summary, connection stats refreshed

### Test Coverage

**89 → 122 tests (+33 new)**

| Test File | Count | Covers |
|-----------|-------|--------|
| test_daydream.py | 23 | Gates, self-check, pattern pulse, creative association, logging, full cycle |
| test_hook.py | 41 | Keywords, behavioral inference, priming, run_hook() integration (4 new) |
| test_mycelial.py | 37 | Nodes, connections, co-occurrence, decay, stats, cluster BFS (4 new), anastomosis (2 new), transactions (2 new) |
| test_consolidate.py | 9 | Decay orchestration, scout promotion, idempotency, transcript processing |
| test_retroactive.py | 8 | Weight calculations, unknown concepts, case normalization, activation logging |
| test_assembler.py | 14 | Startup assembly, budgets, file detection |

### Remaining Work (Phases 3-5)

Organized in `agent/memory/working/wm-review-phases.md`:
- **Phase 3** — Hook quality & detection (7 items): regex precompilation, false positive fixes, error logging
- **Phase 4** — Infrastructure hardening (7 items): start.bat validation, nap quiesce, dream.sh permissions
- **Phase 5** — Architecture evolution (12 items): minion migration to `.claude/agents/`, memory frontmatter, UserPromptSubmit hook, Magic Docs, Skill Improvement

### Stats

- 25 sessions over 19 days (2026-03-14 to 2026-04-02)
- 8 minion personalities (Strut, Lint, Riff, Wren, Tack, Marshal, Fallow, Spec)
- 11 dashboard views
- 122 unit tests
