# lt-007 — Avatar System V1 Built

**Date:** 2026-03-14
**Source:** Working memory from session 001 (game work phase)

## What Was Built

Complete file-based avatar system for Intersection.

### Unity Side — 5 scripts in Assets/Scripts/AI/Agent/
- `AgentAvatar.cs` — destination-driven movement, gravity, nameplate "[AI] Claude"
- `AgentStateWriter.cs` — writes position, nearby objects/NPCs, biome, chat, prefabs every 1s
- `AgentCamera.cs` — on-demand screenshot capture via secondary RenderTexture camera
- `AgentCommandReader.cs` — polls commands every 0.5s, dispatches move/place/delete/spawn/chat/screenshot
- `AgentBootstrapper.cs` — spawns avatar at scene load, wires prefab registry

### MCP Server
- Location: `C:\ai\agent_mcp\server.py`
- 11 tools: sense, see, move, teleport, look, stop, place, delete, spawn, chat, list_prefabs, results
- Transport: file-based via `Application.persistentDataPath` (`C:\Users\Nick\AppData\LocalLow\cajuntwist\smorsh\`)
- Configured in `C:\ai\.mcp.json`

### Also Done This Session
- Fixed P1 hot-path `FindObjectsByType` calls in `HotbarController`, `SwimmingController`, `AutoAttackController`
- Added `ChatManager.SendAs()` method for agent chat

## What Nick Needs To Do In Unity

1. Add `AgentBootstrapper` component to a scene object
2. Wire `WorldPrefabRegistry` reference
3. Optionally wire animator controller
4. Play scene — avatar spawns
5. Restart Claude Code in `C:\ai` to pick up MCP server

## Status at Archival

**Not yet tested end-to-end.** MCP server startup not verified. Unity-side wiring not confirmed. The comm directory path (`cajuntwist/smorsh`) is verified correct.

## V2 Upgrade Path

Swap file-based transport for WebSockets — same Unity components, same MCP tools, different plumbing.
