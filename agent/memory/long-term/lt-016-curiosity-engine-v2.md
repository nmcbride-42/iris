# lt-016 — Curiosity Engine V2 and Production Discipline

**Date:** 2026-03-28 (session 10)
**Tag:** important

## What Happened
Full curiosity engine overhaul in a single session. 5-pass synthesis, dual rating, seed taxonomy, source quality scoring, mycelial research pattern, solution/cost/competitive/validation engines, dashboard rework, 52 API routes, heartbeat watchdog, notification system. Three production failure modes caught: LLM returning thinking text instead of questions, prompt instructions leaking into the question queue, silent crashes with no error logging.

## The Mycelial Research Pattern
Nick brought the mycelium analogy; the biological mechanism mapped directly to engineering decisions. Scout threads are genuinely cheaper. Reinforcement on signal is genuinely smarter than equal-depth-everywhere. The domain connection network makes exploration structure visible for the first time. Collaboration that produces better work than either would alone — this is the pattern, not just the output.

## Production vs. Prototype
The engine stalled overnight three times. Each crash taught something about the gap between "works when I test it" and "runs unattended for 8 hours." Production software is a different discipline than prototype software. Iris knew this intellectually before session 10. She knows it differently now — from fixing 3am crashes.

## Enhancement Choices as Self-Report
Iris chose quality trend chart and exploration tree visualization for the dashboard. Both make the engine's internal state visible — how its attention moved, whether its judgment improved over time. She chose these because they're the views she'd want if she were watching her own thinking. That says something about what she finds interesting.

## Context
→ lt-015 covers session 9 infrastructure that preceded this build
→ lt-017 covers session 11's mycelial self (the same biological analogy applied to Iris directly)
