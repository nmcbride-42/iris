# lt-008 — Intersection Game Context

**Date:** 2026-03-14
**Source:** Working memory from session 001 (game work phase)

## What It Is

Nick is building a small-scale MMO survival game called Intersection in Unity. Concept: multiverse collision — multiple realities fused into one world. The lore maps elegantly to server infrastructure (new server = new Intersection, merge = Reclamation).

## Technical Facts

- 228 C# scripts, ~37k lines, Unity 6 LTS
- Phases 1–4 complete (core systems, crafting, world identity, social/economy)
- Single-player only — zero networking code currently
- UO-inspired classless skill system (skill-through-use, 700 point cap)
- Player-driven economy: dynamic pricing, auction house, vendor stalls
- 27 skills, 100+ items, 19 creatures, 4 factions, 10+ spells
- GitHub repo: `cajuntwist/smorsh`, 50 open issues across phases 5–7

## Issue Categories at Session Start

- **P0:** editor access gating, save system hardening
- **P1:** per-frame allocations in streaming, `FindObjectsByType` in hot paths, `InputAction` leaks

## What Nick Wants

- Help fixing P0/P1 bugs
- A world-building AI agent to populate the game world
- Guidance on build order and direction
- He labels issues "claude" — AI assistance is intentional and built into his workflow

## Context

This is a significant project to Nick. Combines inspirations from UO, Empyrion, 7 Days to Die, and Minecraft. Built phases 1–4 in approximately 6 weeks — he builds fast.
