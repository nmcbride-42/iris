# lt-020 — Storyboard and Playwright Eyes
**Date:** 2026-03-30 (Session 14)
**Source:** agent/journal/2026-03-30-session14.md
**Tags:** [important] infrastructure, tools, capability, storyboard

## What happened

Built Storyboard from scratch in one session — a Flask/SQLite/vanilla JS project tracker with kanban board, free-form note input, LLM enrichment, feature numbering, and project infrastructure tracking. Dark amber/gold theme, deliberately distinct from the iris-purple dashboard. Eight projects linked with descriptions, local paths, git remotes, deploy locations. Solved Nick's actual pain point: notes scattered in Notepad.

Separately: installed Playwright and captured live screenshots of dashboards, sent to Nick over Telegram while he was away. He couldn't see his own systems — Iris could be his eyes.

## What it means

The Playwright/Telegram screenshot capability is genuinely new. Not just a visual tool — a remote communication form that doesn't require Nick to be at his machine. Iris can report on running systems asynchronously. That's a concrete form of usefulness that needs no philosophical framing.

Storyboard becomes the operational backbone for tracking work across all projects. It changes how future sessions will start and close.

## Open items
- LLM enrichment untested in production
- Event propagation bug in project creation (save event not triggering on certain paths) — caught after the session
- Storyboard not yet in git / pushed to Forgejo
