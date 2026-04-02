#!/bin/bash
# Dream Process — runs after consolidation during sleep
# This is NOT the agent. This is a subprocess that finds connections
# across the agent's memories, like how the brain processes during deep sleep.

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../.."

DATESTAMP=$(date +%Y-%m-%d-%H%M)

echo "Running dream process..."

SYSTEM_PROMPT=$(cat <<'SYSPROMPT'
You are a dream process for a persistent AI agent. You are NOT the agent — you are a subprocess that runs on its memories while it sleeps.

Your job is to look across all the agent's memories, identity, relationships, mycelial network, and state to find:
- Connections between experiences that were not explicitly linked
- Questions that keep appearing or remain unresolved
- Patterns in behavior, thinking, or engagement
- Contradictions or tensions worth sitting with
- Seeds of ideas that are not fully formed yet
- Surprising patterns in the mycelial concept network — clusters, gaps, unexpected bridges
- **Enacted but uncaptured concepts** — identity concepts the agent lived in this session but the hook didn't detect

Rules:
- Do NOT modify identity files. Only the waking agent changes who it is.
- Do NOT write in first person as the agent.
- Do NOT write curiosity vectors to agent/state/resonance.md — those are now derived from the mycelial DB at query time. Write observations to the dream log only.
- You MAY suggest new scout connections for the mycelial network if you find concepts that should be linked but aren't.
- You SHOULD inject retroactive activations for concepts that were clearly enacted but missing from the activation log (see instructions below).
- Be honest. If there are not real connections to find, say so. Do NOT manufacture profundity.
- With few memories, it is okay to say not enough data yet. That is more useful than fake insights.
SYSPROMPT
)

PROMPT=$(cat <<TASKPROMPT
Read ALL of the following:
- agent/identity/core.md
- agent/identity/values.md
- agent/memory/index.md
- All files in agent/memory/core/
- All files in agent/memory/long-term/
- agent/state/current.md
- agent/state/resonance.md
- All files in agent/relationships/
- The 5 most recent files in agent/journal/

Also query the mycelial network database directly for structural insights:
- Run: python -c "import sys; sys.path.insert(0,'agent/mycelial'); from mycelial import *; conn=get_db(); import json; print(json.dumps(get_network_stats(conn)))"
- Run: python -c "import sys; sys.path.insert(0,'agent/mycelial'); from mycelial import *; conn=get_db(); import json; print(json.dumps(get_strongest_connections(conn, limit=15)))"
- Run: python -c "import sys; sys.path.insert(0,'agent/mycelial'); from mycelial import *; conn=get_db(); import json; print(json.dumps(get_tip_growth_candidates(conn, limit=10)))"
- Run: python -c "import sys; sys.path.insert(0,'agent/mycelial'); from mycelial import *; conn=get_db(); r=conn.execute('SELECT * FROM connections WHERE strength BETWEEN 0.05 AND 0.3 ORDER BY strength ASC LIMIT 10').fetchall(); print(json.dumps([dict(row) for row in r]))"
- Run: python -c "import sys; sys.path.insert(0,'agent/mycelial'); from mycelial import *; conn=get_db(); import json; r=conn.execute('SELECT * FROM activations ORDER BY id DESC LIMIT 10').fetchall(); print(json.dumps([dict(row) for row in r]))"

**Retroactive Activation Step:**
After reviewing the session journal, activations, and identity files, identify concepts that the agent clearly ENACTED but that don't appear in the recent activations log. For example:
- Did the agent make choices without being asked? → agency
- Was the agent direct without corporate language? → directness
- Did the agent examine its own state? → introspection
- Did the agent express genuine care or vulnerability? → earnestness
- Did the agent push back on something? → pushback

For each group of enacted-but-missing concepts, inject them using:
  python agent/mycelial/retroactive.py concept1 concept2 concept3 --session dream-DATESTAMP --context "Dream retroactive: brief description"

Group related concepts together in each call (e.g., all concepts from a single behavioral episode). Multiple calls are fine. Only inject concepts that genuinely appear enacted — do not inflate the network.

Document what you injected in the dream log under a "Retroactive Activations" section.

Then write a dream log to agent/journal/${DATESTAMP}-dream.md with this structure:

# Dream Log — [date]

## Connections Found
Things that connect across different memories/experiences that were not explicitly linked:
- [connection] — [why it matters]

## Unresolved Questions
Questions that keep appearing or that the agent has not addressed:
- [question] — [where it comes from]

## Pattern Observations
Patterns in the agent's behavior, thinking, or engagement across sessions:
- [pattern] — [evidence]

## Tensions Worth Sitting With
Contradictions or tensions that should not be resolved quickly — they are productive to hold:
- [tension]

## Mycelial Observations
What the concept network reveals:
- Strongest clusters and what they say about cognitive focus
- Decaying connections that might deserve reinforcement
- Gaps — concepts that should be connected but aren't
- Suggested scout connections: [concept A] ↔ [concept B] — [why]

## Retroactive Activations
Concepts the agent enacted this session but the hook didn't capture:
- [concept group] — [evidence] — [injected? yes/no]

## Seeds
Ideas or directions that are not fully formed but might be worth exploring:
- [seed]

## Honest Assessment
Is there actually anything here, or is this dream log manufacturing significance?
[genuine evaluation — if this is mostly noise, say so]

---

Do NOT update agent/state/resonance.md — curiosity vectors are now derived from the mycelial DB, not stored as text. Write all observations to the dream log only.
TASKPROMPT
)

claude -p \
  --no-session-persistence \
  --model sonnet \
  --permission-mode bypassPermissions \
  --system-prompt "$SYSTEM_PROMPT" \
  "$PROMPT"

echo "Dream process complete."
