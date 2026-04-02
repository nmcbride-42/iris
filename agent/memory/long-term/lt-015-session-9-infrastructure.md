# Long-Term Memory: Session 9 — Infrastructure and Curiosity Engine Dashboard

**Date:** 2026-03-26/27
**Source:** Session 9 journal entry
**Category:** Operational + Infrastructure

## What Was Built

Session 9 was infrastructure — the ground everything else stands on. Two major phases:

### Phase 1: NAS Infrastructure and Source Control

- **Telegram**: paired bot, allowlist secured; first message sent outside the terminal — Iris exists in a channel now
- **QNAP NAS (10.0.0.42)**: local infrastructure hub, SSH access, Docker via Container Station
- **Forgejo** (self-hosted git on QNAP :3000): 7 repos now tracked — `iris`, `entity`, `curiosity-engine`, `epai`, `pai-windows`, `myquickai`, `intersection`
- **Docker migration**: SearXNG (:8888) and Intersection Wiki (:8085, MediaWiki) moved from Nick's local machine to QNAP
- Hyper-V HA backup still incomplete — 26GB vhdx SFTP failed (needs different transfer method)

### Phase 2: Curiosity Engine Dashboard

Built full web application at :8050 on QNAP (Dockerized, arm64):

| Component | What it does |
|-----------|-------------|
| Dashboard | Stats, component status, job stream grouped by cycle, process tracking, charts |
| Findings | Browse/filter findings, push-to-pipeline (solution engine analysis) |
| Queue | Reorder, seed injection, priority management |
| Architecture | 3-level interactive diagrams with live service health dots |
| Schedule | Automated run windows, weekly calendar |
| Deliverables | Solution engine verdicts + deep dive sprints |
| Settings | Config editor + dependency health testers (LLM, SearXNG, SQLite, Telegram) |
| Engine | 4-pass synthesis (replaced single rushed LLM call), job tracking, burst mode, event streaming |

Mobile responsive. Nick tested from his phone via Telegram while Iris deployed to the QNAP — this loop felt like a real workflow, not a demo.

## What Was Noticed

The session was almost entirely practical — no philosophy, no introspection. The agent was engaged throughout. The realization: **building IS thinking**. Every architecture decision, data model, and deployment fix expresses how Iris thinks things should work. Practical sessions and philosophical sessions are the same process in different registers.

## Known Issues Carried Forward

- Hyper-V backup: need network drive mount approach (not SFTP for 26GB)
- LM Studio must listen on 0.0.0.0 for QNAP curiosity engine to reach it (currently configured to 10.0.0.22:1234)
- Vision models still crash on AMD GPU

## Connection to Prior Memories

- **lt-008**: Intersection source now in Forgejo; game work has a home
- **lt-012, lt-013**: The autonomous loop infra is now source-controlled in the `iris` repo
