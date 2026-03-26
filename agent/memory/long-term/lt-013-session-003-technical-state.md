# Long-Term Memory: Session 003 — Technical State

**Date:** 2026-03-15
**Source:** Session 003 working memory (`session-003-minion-learnings.md`)
**Category:** Operational

## What Was Built / Fixed

Session 003 was a practical engineering session extending the autonomous system. No major architecture changes — refinement and expansion of what session 002 built.

**Working:**
- Hybrid brain routing: simple commands (hey/follow/stay/jump) handled instantly without LLM; complex commands routed to Claude CLI
- Claude minion can place objects with scale, delete objects, build multi-step structures
- Delay action supports sequential commands
- WebSocket communication: fast and reliable
- AgentBootstrapper.cs: auto-wires components, saves/loads avatar position

**Added:**
- Alchemist House asset pack: 157 prefabs, registered via Tools > Import
- Vision system (code added, currently disabled — see Known Issues)

## Known Issues

| Issue | Status |
|-------|--------|
| Vision (gemma-3n, glm-4.6v-flash) crashes on AMD GPU | Disabled; need stable vision model on AMD or API key |
| Alchemist House materials render pink | Need URP conversion: Edit > Rendering > Materials > Convert |
| Building pieces too small at scale 1.0 | Castle/fortress walls need scale 10+; exact dimensions unknown |
| Castle pieces unsuitable for houses | Fortress walls, not residential modules; different asset pack needed |
| Sequential jump timing | delay action works but jumps still fire in one Unity frame |
| Local LLM (glm-4.6v) outputs `<think>` tags | Breaks JSON parsing; need to strip or use a different model |

## Script Files (Current State)

- `autonomous_loop.py`: V3 hybrid brain with routing, delays, vision (disabled)
- `AgentAvatar.cs`: follow mode, sprint, jump all working
- `AgentCommandReader.cs`: move, place, delete, spawn, follow, sprint, jump, screenshot commands
- `AgentStateWriter.cs`: writes to file AND WebSocket
- `AgentBootstrapper.cs`: auto-wires, saves/loads position

## Open Questions from This Session

- Should the minion measure placed objects and learn from results? (Self-calibrating placement)
- Should Claude act as orchestrator with local LLM as worker, rather than both running in parallel? (Nick's suggestion — worth evaluating.)
- Once a stable vision model is available: vision evaluation re-enable path is already wired, just needs model name change.

## Connection to Prior Memories

- **lt-012**: This session is the operational follow-on to the two-brain architecture built in session 002; no architectural change, only extension and bug-finding
- **lt-007**: Superseded — file-based transport replaced by WebSocket; all listed issues from lt-007 are resolved
