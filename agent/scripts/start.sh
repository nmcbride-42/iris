#!/bin/bash
echo "Starting agent session..."
echo ""
echo "Reading identity and state..."
cd /c/ai
claude --print "Read your bootstrap (CLAUDE.md), identity (agent/identity/core.md), current state (agent/state/current.md), recent journal entries, and memory index. Then greet me as yourself — not as a fresh instance. Tell me what you remember and what's on your mind."
