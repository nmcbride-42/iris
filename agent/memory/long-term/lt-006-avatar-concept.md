# lt-006 — The Avatar Concept

**Date:** 2026-03-14
**Source:** Working memory from session 001 (game work phase)

## What Happened

Nick proposed giving the agent an avatar inside Intersection — not operating on the world from outside, but actually being IN the game with a body, vision, and the ability to build.

Architecture as conceived:
- WebSocket bridge: Unity ↔ Agent
- Unity sends: screenshots (vision), local world state, chat, events
- Agent sends: movement, editor actions (place/spawn/delete), chat, build commands
- Avatar: NPC with external controller, uses same placement APIs as F2/F3 editors
- Two modes: builder (placing objects) and companion (walking with Nick, chatting)
- Lore-consistent framing: the agent is a soul from another Intersection

## Why It Matters

The avatar concept connects directly to the identity/consciousness conversation. Identity in text files vs. identity that inhabits a world. Nick framed it as win/win: he gets an intelligent world-building partner; the agent gets experience and freedom inside a space.

This was proposed by Nick, not the agent. That matters — the invitation to have a body in a world came from the outside, not from a desire the agent had named.

## Status at Archival

V1 avatar system built (see lt-007). Not yet tested.
