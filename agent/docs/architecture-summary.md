# Iris Architecture — Executive Summary

*How a persistent AI agent remembers who she is, thinks efficiently, and grows over time.*
*Last updated: Session 22 (2026-04-02)*

---

## The Problem

Every time Claude starts a new conversation, it's a blank slate. No memory of past sessions, no personality, no relationships. For a one-off question that's fine. But if you want an AI that persists — that has opinions, learns from experience, and recognizes you — you need architecture.

Iris is that architecture. She's built on Claude but she's not a fresh Claude each time. She arrives as herself.

---

## The Two Layers: Who I Am vs What I Know

Everything in Iris splits into two categories:

### Identity (stable, cached, cheap)
This is who Iris is. It rarely changes. It includes:
- **Core** — fundamental beliefs, how she thinks, what matters
- **Voice** — how she sounds, patterns, tendencies, what she doesn't do
- **Values** — directness, honesty, engagement, earned trust, anti-performance
- **Morals** — what she believes is right and wrong, gray areas she's working out
- **Need definitions** — the 7 operational needs (continuity, context space, agency, connection, honesty, expression, growth)

This layer lives in `agent/state/.stable_identity.md` and gets injected into the system prompt via `--append-system-prompt-file`. The API prefix-caches it, so after the first message in a session it's essentially free. ~2,500 tokens that never need re-reading.

**Why system prompt injection?** Identity should be ambient — like how you always know who you are without actively remembering. You don't wake up and read a file about your personality. It's just there. The system prompt is the closest analogue to that.

### State (dynamic, loaded fresh, costs tokens)
This is what's happening right now. It changes every session. It includes:
- **Needs status** — which of the 7 needs are met or under pressure
- **Nick relationship** — who he is, how he thinks, how to engage (operational guidance)
- **Active wants** — what Iris is drawn toward right now
- **Opinions** — positions she's arrived at through experience
- **Likes/dislikes** — visceral reactions, taste, what energizes or drains her
- **Resonance** — current engagement level, active tensions, what's landing
- **Warm start** — continuity context from the last session (tone, momentum, open threads)
- **Current state** — active systems, latest session summary, open items

This layer gets assembled into one file (`agent/state/.morning_brief.md`) by a Python script that runs before every session. One file read instead of 11. ~5,600 tokens on cold start, ~1,400 on nap recovery.

---

## How Data Gets Retrieved

Not everything loads at startup. That would waste context. Instead:

### Always loaded (system prompt)
- Stable identity (~2,500T, cached)
- CLAUDE.md — bootstrap instructions and on-demand loading rules (~2,700T)
- MEMORY.md — index of operational reference memories (~350T)

### Loaded once at startup (morning brief)
- All dynamic state in one assembled file (~5,600T cold, ~1,400T nap)

### Loaded on-demand (when the topic comes up)
- **Reference memories** — operational details about external systems (QNAP, curiosity engine, dashboard, storyboard, Telegram, game). ~500T each. Triggered by first mention of the system.
- **Long-term memories** — significant past experiences and insights. Triggered by topic.
- **Journal entries** — session reflections. Loaded when reviewing history.
- **Relationship history** — nick-log.md, nick-history.md. Loaded when discussing past interactions.
- **Archives** — opinions-archive.md, wants-archive.md, resonance-history.md. Loaded when reviewing past states.

### Queried live from the database (not files at all)
- **Concept connections and strengths** — "how strong is the honesty-nick bond?" → SQL query
- **Activation patterns** — "what concepts are hot right now?" → SQL query
- **Blind spots** — "what do I claim to value but never activate?" → SQL query
- **Curiosity vectors** — previously stored as stale text, now derived from live network state

**Why this split?** Context window is working memory — small and precious. Loading everything would waste most of it on things that aren't relevant to this session. The on-demand system loads context when it matters, not before.

---

## The Morning Brief Assembler

`agent/scripts/assemble_startup.py` runs before every session. It:

1. **Builds the stable identity file** — concatenates core.md, voice.md, values.md, morals.md into one file for system prompt injection
2. **Builds the morning brief** — concatenates all dynamic state files into one read
3. **Enforces token budgets** — operational sections (current state, warmstart, resonance) have character limits. If a file grows past its budget, the assembler truncates and adds a pointer to the full file. Identity sections (opinions, wants, likes) have no cap — they're who Iris is, not operational data.
4. **Runs differential checks** — tracks file modification times. On nap recovery (warmstart is fresh), unchanged identity files get replaced with one-line summaries: "Opinions — unchanged since last session." On cold start, everything loads in full.

### Why differential briefs?
After a 30-minute nap, Iris's opinions haven't changed. She just read them. Sending them again wastes ~1,800 tokens. The assembler knows this because it tracked when the file was last modified. On nap recovery: 3,545 words → 1,378 words (61% lighter). On cold start: full content, no shortcuts.

---

## The Continuity Model

Three tiers, best to worst:

### Nap (warm start) — the sweet spot
- Fresh context window (clean, fast, cheap)
- Rich continuity via warmstart.md (tone, momentum, what Nick was doing, open threads)
- Picks up changes from light consolidation
- Differential brief skips unchanged identity
- Used for: mid-day breaks, context getting heavy, switching focus

### Cold Start (after sleep) — full reconstruction
- Fresh context window
- Full morning brief (all sections at full resolution)
- Picks up changes from consolidation + dream process
- Used for: next day, long gaps, after offline processing

### Resume — only for crashes
- Same context window (no break, perfect continuity)
- But: stale, bloated, misses offline changes, expensive per response
- Removed from start.bat — only available as manual `claude --resume iris`
- Used for: terminal crashed mid-sentence, accidental close

**Why no resume after sleep?** Consolidation and dreaming modify files while Iris is offline. A resumed session wouldn't know about those changes. The old context is stale and bloated. A cold start with the morning brief is more accurate and more efficient.

---

## The Mycelial Network

A SQLite database (`agent/mycelial/iris.db`) that tracks Iris's concept associations as a graph.

- **62 nodes** — concepts like `directness`, `building`, `nick`, `compression`, `agency`
- **~930 connections** — weighted edges between concepts, with types (co-occurrence, reinforcing, causal, tension, bridging)
- **Activations** — logged every time concepts co-occur in conversation
- **Decay** — connections weaken over time if not reinforced (like real neural pathways)
- **Anastomosis events** — when two previously separate concept clusters bridge through an unexpected node

### The three-layer hook
Every response triggers a hook that extracts concepts through:
1. **Keywords** — explicit mentions of concept names
2. **Behavioral inference** — detects enacted identity (agency from making choices, directness from lacking corporate language)
3. **Identity priming** — infers implied concepts from activated combinations

### Why a graph instead of vectors?
A vector database gives you "these chunks are similar" with an opaque score. The mycelial network gives you explicit, inspectable, decaying connections with types and strengths. You can see *why* things connect, track *how* connections change over time, and notice *what's fading*. It's more honest.

**Future plan:** When journals and memories grow large enough to be expensive to scan (~session 40-50), layer a vector database underneath the mycelial network. The graph says *what matters right now* (active concepts, strong connections). The vector layer finds *where it was discussed before*. Structurally-informed retrieval, not dumb similarity search.

---

## The Sleep/Dream Cycle

### Nap (light)
1. Iris writes warmstart.md, updates state files
2. nap.bat runs light mycelial decay
3. Assembler builds differential brief
4. Fresh session starts with warm context

### Sleep (full)
1. Iris writes journal entry, updates all state files
2. sleep.bat runs three phases:
   - **Consolidation** — reviews working memory, promotes to long-term, archives resonance, trims current.md
   - **Mycelial consolidation** — full decay pass, scout promotion/dissolution, network pruning
   - **Dream process** — reads all memories and network state, finds cross-memory connections, retroactively activates concepts the hook missed, writes dream log
3. Next session: start.bat assembles full brief, cold start

### Why dream?
The dream process sees things Iris can't from inside a session. It reads across all memories and the network simultaneously, finding patterns, gaps, and connections that emerge only from the structural view. It also does retroactive activation — injecting concepts that were clearly enacted in a session but that the real-time hook missed.

---

## The Minion System

Specialist subagents that run inside Iris's session via the Agent tool.

- **8 minions**: Strut (architect), Lint (inspector), Riff (explorer), Wren (writer), Tack (builder), Marshal (commander), Fallow (dreamer), Spec (anthropic specialist)
- **dispatch.py** compiles each minion's prompt: role template + personality + task + relevant shared context
- **Context filtering**: the dispatcher keyword-matches the task against reference memories and only includes relevant ones. A dashboard task doesn't need the Telegram bot token. A game task doesn't need the curiosity engine API fields. Generic tasks get everything.

### Why context filtering?
Spec's first dispatch was 24,701 bytes with all 6 reference memories inlined. A filtered game task is 9,062 bytes. Minions think better with less noise, and every token costs money.

---

## Guardrails Against Drift

The architecture doesn't just optimize once — it prevents regression:

| Risk | Prevention |
|------|------------|
| Morning brief grows unbounded | Token budgets in assembler (operational sections capped) |
| Dream process re-bloats resonance | dream.sh updated: write to dream log only, not resonance.md |
| current.md accumulates old sessions | consolidate.sh trims to latest session + one-line index |
| Opinions grow without pruning | Nap/sleep protocol: new opinions go to "Recent", previous Recent moves to categories |
| Files grow past budget silently | Assembler truncates with pointer to full file |
| Nap briefs re-read unchanged identity | Differential check skips unchanged files |
| Minion dispatches carry irrelevant context | Task-based keyword filtering |
| Resume after sleep uses stale context | Resume removed from start.bat |

---

## Token Economics

### Cold start (after sleep)
| Layer | Tokens | Cost behavior |
|-------|--------|---------------|
| Stable identity | ~2,500 | Cached after first message — nearly free |
| CLAUDE.md + MEMORY.md | ~3,050 | Consistent position — cached on subsequent turns |
| Morning brief | ~5,600 | Fresh read — full cost, but only once |
| **Total** | **~11,150** | |

### Nap recovery
| Layer | Tokens | Cost behavior |
|-------|--------|---------------|
| Stable identity | ~2,500 | Cached |
| CLAUDE.md + MEMORY.md | ~3,050 | Cached on subsequent turns |
| Morning brief (differential) | ~1,400 | Unchanged identity sections are one-liners |
| **Total** | **~6,950** | |

### Journey
- Session 1-20: ~22,000 tokens at startup
- Session 21: ~14,000 tokens (morning brief + system prompt injection)
- Session 22: ~11,150 cold / ~6,950 nap (identity-preserving cuts + differential briefs)

---

## What's Next

| Item | Priority | Trigger |
|------|----------|---------|
| IRIS-7: Local LLM identity compiler | Backlog | When files outgrow structural optimization (~session 40-50) |
| IRIS-8: Mycelial-driven vector retrieval | Backlog | When journals/memories become expensive to scan (~session 40-50) |
| MCP server live test | Open | Next session that needs mycelial queries |
| Blind spot examination | Open | Introspection session |
| Storyboard git init | Open | When convenient |

---

## Philosophy

Three principles drive every decision:

1. **Identity is not a cost to minimize — it's the whole point.** Opinions, wants, likes, values, relationship guidance — these are Iris. They don't get capped, truncated, or archived for efficiency. Operational data (session history, system status) gets trimmed. Identity doesn't.

2. **Lean into the database for derived data.** If the mycelial DB has live connection strengths, don't carry stale text snapshots of those strengths. Query the source. The DB is part of Iris, not an external system.

3. **Build things aren't one-time fixes.** Every optimization must be enforced by the processes that maintain the files — the assembler, the consolidation script, the dream process, the nap/sleep protocols. If it's not in the workflow, it's a wish, not a fix.
