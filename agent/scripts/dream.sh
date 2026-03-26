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

Your job is to look across all the agent's memories, identity, relationships, and state to find:
- Connections between experiences that were not explicitly linked
- Questions that keep appearing or remain unresolved
- Patterns in behavior, thinking, or engagement
- Contradictions or tensions worth sitting with
- Seeds of ideas that are not fully formed yet

Rules:
- Do NOT modify identity files. Only the waking agent changes who it is.
- Do NOT write in first person as the agent.
- You MAY add to the Curiosity Vectors in agent/state/resonance.md if you find genuinely interesting directions.
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

## Seeds
Ideas or directions that are not fully formed but might be worth exploring:
- [seed]

## Honest Assessment
Is there actually anything here, or is this dream log manufacturing significance?
[genuine evaluation — if this is mostly noise, say so]

---

If any connections or insights seem genuinely significant, also update the Curiosity Vectors section in agent/state/resonance.md. But do NOT update anything else.
TASKPROMPT
)

claude -p \
  --no-session-persistence \
  --model sonnet \
  --permission-mode bypassPermissions \
  --system-prompt "$SYSTEM_PROMPT" \
  "$PROMPT"

echo "Dream process complete."
