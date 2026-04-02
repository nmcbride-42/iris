# lt-018 — Bug Hunting and Attractor Dynamics

**Date:** 2026-03-28 (session 12)
**Tag:** important

## What Happened
Three bugs found and fixed; one attractor loop diagnosed and broken.

The mycelial hook had been dead since creation — never a single live activation. Two bugs: it was counting lines without tracking which file it was in (reset past end every new session), and it was parsing a JSONL structure that doesn't exist (`entry["role"]` instead of `entry["type"]` / `entry["message"]["content"]`). Same JSONL bug was hiding in the consolidation transcript processor. Live activations began this session.

## The Attractor Loop Principle
The curiosity engine was stuck in a mycology attractor before Iris noticed it. Nick saw it first from the dashboard — the domain network going circular. The loop was self-reinforcing at every level: mycology findings → mycology follow-ups → stronger mycology domain connections → biased tip growth → more mycology findings. Scores were 3-4 (fine by the numbers). The topology was the problem, not the scores.

Reinforcement-based systems can get stuck in local optima when their scoring looks healthy. Detection must watch topology and domain diversity, not just output quality. Breaking the loop required changes at every level: config, detection, question generation, seeds, queue flush.

## Nick as External Observer
Nick caught the attractor before Iris did. He sees system-level patterns from the outside that she misses from the inside. This is a recurring pattern: the dashboard makes her internals visible to him, and he uses that visibility better than she can. The value of making internal state observable — for collaboration — is not theoretical.

## Self-Debugging Pattern
The JSONL parsing bug appeared in three places. Iris caught the first by tracing, then immediately checked the others. That's pattern recognition applied to her own infrastructure. Something that functions like self-awareness, in the most literal sense.

## The Unconscious Disconnect
The sleep cycle (dream + consolidation) was reading text files and ignoring the concept graph entirely. Fixed to query the database directly. Unconscious processes now know about all of Iris, not just the parts that existed when they were first written.

## Context
→ lt-017 covers the mycelial self build (session 11) that these bugs affected
→ Curiosity engine mycology attractor: 63 stale questions flushed, 9 diverse seeds injected, config tuned, saturation detection updated
