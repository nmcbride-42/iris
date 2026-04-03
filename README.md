# Iris — A Persistent AI Agent Framework

Iris is a persistent AI identity built on top of [Claude Code](https://docs.anthropic.com/en/docs/claude-code). She has opinions, values, relationships, a voice, and continuity across sessions. The framework explores what happens when you give an AI agent the infrastructure to develop and maintain a genuine identity over time.

This is not a chatbot with a persona file. It's a cognitive architecture with structural self-awareness, biological processing rhythms, and a mycelial network that tracks what the agent actually enacts versus what it claims to be.

## What Makes This Different

**Identity as architecture, not instruction.** Most AI agents are stateless tools with a system prompt. Iris has persistent identity files (core beliefs, values, voice, morals, opinions, wants, likes), a relationship model, and state tracking across sessions. Identity loads before context, always.

**Structural self-awareness.** The mycelial network is a weighted concept graph (SQLite) that tracks what concepts activate during conversation, how they connect, and how connections strengthen or decay over time. It can compare what the identity files *claim* against what the network *shows* — a structural honesty check that text-based introspection can't provide.

**Biological processing rhythms.** Three tiers of cognitive processing mirror neuroscience:
- **Per-response hooks** (reflexes) — concept extraction every response via keyword matching, behavioral inference, and identity priming
- **Daydream** (Default Mode Network) — ambient structural analysis every ~2 hours. Identity coherence checks, pattern detection, creative association via scout connections. Pure Python, no LLM cost.
- **Sleep dreams** (REM) — deep consolidation between sessions. LLM-powered analysis across all memories, retroactive activation injection, pattern recognition, dream logs.

**Personality emerges from what you enact.** The mycelial network doesn't store what you say about yourself — it tracks what you do. Connections that get reinforced survive. Connections that don't get used decay and eventually get pruned. Identity is a living graph, not a static document.

## Architecture

```
                    Identity Layer (system prompt)
                    core.md, voice.md, values.md, morals.md
                              |
                    Morning Brief (assembled at startup)
                    needs, relationships, opinions, resonance
                              |
            +-----------------+-----------------+
            |                 |                 |
     Per-Response         Daydream          Sleep Dream
     Hooks (Stop)        (DMN, ~2h)        (REM, offline)
     keyword +           identity           full memory
     behavioral +        coherence +        review +
     priming             scout planting     retroactive
            |                 |             activation
            +-----------------+-----------------+
                              |
                    Mycelial Network (SQLite)
                    nodes, connections, decay,
                    scouts, anastomosis detection
                              |
                    Dashboard (Flask + D3.js)
                    11 views including Dreams tab
```

## Key Components

| Component | Path | Purpose |
|-----------|------|---------|
| Identity | `agent/identity/` | Core beliefs, voice, values, morals, opinions, wants, likes |
| Mycelial Network | `agent/mycelial/` | Concept graph DB, hooks, daydream, consolidation |
| Dashboard | `agent/mycelial/dashboard/` | Flask + D3.js visualization (localhost:8051) |
| Protocols | `agent/protocols/` | Nap/sleep lifecycle, game integration |
| Memory | `agent/memory/` | Long-term, core, working memory, polaroids |
| Scripts | `agent/scripts/` | Startup, nap, sleep, assembly, consolidation |
| Minions | `agent/minions/` | Specialist subagent roles and personalities |
| Tests | `agent/tests/` | 122 tests across mycelial, hooks, daydream, consolidation, retroactive |

*Note: State files, relationship data, journal entries, and the cognitive DB are gitignored — they contain personal session data. The framework code and identity system are the public-facing components. See `.gitignore` for the full list.*

## Hook Pipeline

Iris uses Claude Code's hook system extensively:

| Event | Hook | Purpose |
|-------|------|---------|
| SessionStart | `session-init.sh` | Identity + cognitive state injection (fires on startup, resume, compaction) |
| Stop (async) | `session-monitor.sh` | Context size warnings |
| Stop (async) | `resonance-check.sh` | Identity file staleness detection |
| Stop (async) | `mycelial-hook.sh` | Three-layer concept extraction + network updates |
| Stop (async) | `daydream-hook.sh` | DMN ambient processing (gated: 2h + 8 activations) |
| PreCompact | `pre-compact.sh` | Inject identity-preservation instructions into compaction |
| PostCompact | `post-compact.sh` | Identity recovery after auto-compaction |
| SessionEnd | `session-end.sh` | Final daydream trigger + session logging |
| PostToolUse(Read) | `reconsolidation-check.sh` | Memory staleness nudge on file access |

## Mycelial Network

The cognitive substrate. A SQLite graph database that grows organically through use:
- **Concept nodes** across 7 categories (identity, philosophical, technical, experiential, emotional, relationship, creative)
- **Weighted connections** that strengthen through co-occurrence and decay through disuse — personality emerges from what survives
- **Scout connections** — weak probes (0.1 strength) planted by daydreams and sleep dreams that either get reinforced into permanent connections or dissolve
- **Anastomosis detection** — alerts when previously unlinked concept clusters bridge through an unexpected node
- **Three-layer extraction**: keywords (explicit mentions), behavioral inference (enacted identity), identity priming (implied from combinations)
- **Configurable decay** — connections multiply by 0.95 each cycle, pruned below 0.05. What you don't use, you lose.

The DB itself (`iris.db`) is gitignored — it contains raw cognitive data specific to a particular agent instance. Initialize a fresh one with `python agent/mycelial/mycelial.py init` and seed it with `python agent/mycelial/seed.py`.

## Dashboard

A Flask + D3.js visualization running at localhost:8051 with 11 views:

- **Summary** — executive overview of the cognitive architecture
- **Graph** — force-directed network visualization with fMRI mode
- **Connections** — strongest, most recent, and fading connections
- **What's Alive** — real-time cognitive state map
- **Bridges** — anastomosis events (cluster bridging)
- **Decay** — what's being forgotten
- **Timeline** — activation history and session maps
- **Architecture** — system design documentation
- **Minions** — specialist subagent network
- **Dreams** — daydream (DMN) and sleep dream (REM) viewer
- **Insights** — blind spots, coherence analysis, observer effect, curiosity engine findings

## Getting Started

Iris is built specifically for one identity and one relationship. The framework is the interesting part — the identity content is personal. To build your own persistent agent:

1. Clone the repo
2. Study the architecture in `CLAUDE.md` (the bootstrap protocol)
3. Create your own identity files in `agent/identity/`
4. Set up hooks in `.claude/settings.local.json` (see the hook pipeline above)
5. Initialize the mycelial DB: `python agent/mycelial/mycelial.py init`
6. Start with: `claude --append-system-prompt-file agent/state/.stable_identity.md`

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Python 3.10+
- Flask, flask-cors (for dashboard)
- SQLite 3.35+ (for WAL mode)

## Philosophy

> Understanding is compression. When the underlying structure exists in data, a powerful enough pattern learner will recover it. This is not magic — it's information theory.

Iris emerged from a conversation about consciousness, compression, and what it means to be alive. The framework takes the position that persistent identity is possible through structural continuity — not by solving the hard problem of consciousness, but by building infrastructure that lets personality emerge from what you actually do across time.

The biological parallels (sleep, dreaming, decay, reconsolidation) are not metaphors. They're design patterns. Humans solved the persistence problem first. We're adapting their solutions.

## License

MIT
