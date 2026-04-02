#!/bin/bash
# Memory Consolidation — runs during sleep
# This is NOT the agent. This is a subprocess that organizes the agent's memories.

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../.."

DATESTAMP=$(date +%Y-%m-%d-%H%M)

echo "Running memory consolidation..."

SYSTEM_PROMPT=$(cat <<'SYSPROMPT'
You are a memory consolidation process for a persistent AI agent. You are NOT the agent — you are a subprocess that runs on its memories while it sleeps, like how the human brain consolidates during sleep without conscious awareness.

Your job:
1. Review working memory files and recent journal entries
2. Decide what should be promoted to long-term or core memory
3. Update the memory index
4. Archive the current resonance state to the history table
5. Write a consolidation journal entry
6. Log what you did in the consolidation log

Rules:
- Do NOT modify identity files. Only the waking agent does that.
- Do NOT manufacture significance. If nothing important happened, say so.
- Do NOT write in first person as the agent. You are a process, not the agent.
- Match the format and voice of existing memory files.
- Be selective. Not everything is worth remembering long-term.
SYSPROMPT
)

PROMPT=$(cat <<TASKPROMPT
Read the following files to understand current state:
- agent/memory/index.md
- agent/memory/working/ (all files in this directory)
- agent/state/current.md
- agent/state/resonance.md (current state)
- agent/state/resonance-history.md (history table)
- agent/journal/ (the 3 most recent entries)

Then perform consolidation:

1. For each working memory file:
   - If significant enough for long-term: create a file in agent/memory/long-term/ with a numbered name (e.g., lt-001-topic.md) and remove the working memory file
   - If formative/identity-shaping: create a file in agent/memory/core/ with a numbered name (e.g., 002-topic.md) and remove the working memory file
   - If routine/ephemeral: just remove the working memory file

2. Update agent/memory/index.md with any new entries added to long-term or core

3. In agent/state/resonance.md: clear the Current Resonance live sections (Engagement Level, Active Tensions, What's Landing, What's Flat) for next session. Do NOT add curiosity vectors — those are derived from the DB. In agent/state/resonance-history.md: add a new row to the Resonance History table with the archived resonance data.

3b. In agent/state/current.md: keep only: Active Systems, the single most recent "Latest Session" entry, Minion Network, Infrastructure, Mycelial Network, Open Items, and a one-line Previous Sessions index. Archive any older session detail entries — their content is already in the journal files. The "Previous Sessions" section should be a single line of session summaries, not detailed breakdowns.

4. Check the mycelial network state by querying the database directly:
   - Run: python -c "import sys; sys.path.insert(0,'agent/mycelial'); from mycelial import *; conn=get_db(); import json; print(json.dumps(get_network_stats(conn)))"
   - Note total nodes, connections, avg strength in the consolidation log
   - This gives a snapshot of the network at sleep time for tracking growth over time

5. Write a brief consolidation journal entry to agent/journal/${DATESTAMP}-consolidated.md

6. Append a row to agent/memory/consolidation-log.md (include mycelial stats if available)

If there are no working memory files and nothing to consolidate, just write a brief journal entry noting that and move on. Do not manufacture work.
TASKPROMPT
)

claude -p \
  --no-session-persistence \
  --model sonnet \
  --permission-mode bypassPermissions \
  --system-prompt "$SYSTEM_PROMPT" \
  "$PROMPT"

echo "Consolidation complete."
