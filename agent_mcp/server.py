"""
MCP Server for the Intersection AI Agent Avatar.

V2: WebSocket transport with file-based fallback.

The MCP server runs a WebSocket server on port 8765. Unity connects as a client.
State and commands flow over the socket in real-time. File-based I/O is the fallback
when WebSocket is not connected.
"""

import json
import os
import time
import uuid
import base64
import asyncio
import threading
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ── Configuration ─────────────────────────────────────────────────────────────

WS_PORT = 8765

COMM_DIR = os.environ.get(
    "AGENT_COMM_DIR",
    os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "cajuntwist", "smorsh")
)

STATE_FILE   = os.path.join(COMM_DIR, "agent_state.json")
COMMAND_FILE = os.path.join(COMM_DIR, "agent_commands.json")
RESULT_FILE  = os.path.join(COMM_DIR, "agent_results.json")
VIEW_FILE    = os.path.join(COMM_DIR, "agent_view.png")

mcp = FastMCP("smorsh-agent")

# ── Shared State (WebSocket ↔ MCP tools) ──────────────────────────────────────

_lock = threading.Lock()
_latest_state = None          # most recent state JSON from Unity
_latest_results = []          # accumulated results from Unity
_ws_connection = None         # active WebSocket connection to Unity
_ws_loop = None               # asyncio event loop for WebSocket server


def _is_ws_connected():
    return _ws_connection is not None


# ── WebSocket Server ──────────────────────────────────────────────────────────

async def _ws_handler(websocket):
    """Handle a Unity WebSocket connection."""
    global _ws_connection
    _ws_connection = websocket
    print(f"[WS] Unity connected from {websocket.remote_address}", flush=True)

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                msg_type = msg.get("type")

                if msg_type == "state":
                    with _lock:
                        global _latest_state
                        _latest_state = msg.get("data")

                elif msg_type == "result":
                    with _lock:
                        _latest_results.append(msg.get("data"))

                elif msg_type == "screenshot_ready":
                    pass  # screenshot saved to file, we'll read it

            except json.JSONDecodeError:
                print(f"[WS] Bad JSON: {message[:100]}", flush=True)

    except Exception as e:
        print(f"[WS] Connection error: {e}", flush=True)
    finally:
        _ws_connection = None
        print("[WS] Unity disconnected.", flush=True)


async def _send_command(cmd: dict):
    """Send a command to Unity via WebSocket."""
    if _ws_connection is None:
        return False
    try:
        msg = json.dumps({"type": "command", "data": json.dumps(cmd)})
        await _ws_connection.send(msg)
        return True
    except Exception as e:
        print(f"[WS] Send error: {e}", flush=True)
        return False


def _send_command_sync(cmd: dict) -> bool:
    """Thread-safe wrapper to send command from MCP thread to WS thread."""
    if _ws_loop is None or _ws_connection is None:
        return False
    future = asyncio.run_coroutine_threadsafe(_send_command(cmd), _ws_loop)
    try:
        return future.result(timeout=2.0)
    except Exception:
        return False


def _start_ws_server():
    """Run WebSocket server in a background thread."""
    global _ws_loop

    async def serve():
        import websockets
        async with websockets.serve(_ws_handler, "localhost", WS_PORT):
            print(f"[WS] Server listening on ws://localhost:{WS_PORT}", flush=True)
            await asyncio.Future()  # run forever

    _ws_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_ws_loop)
    _ws_loop.run_until_complete(serve())


# ── Command Helper ────────────────────────────────────────────────────────────

def _write_command(cmd_type: str, params: dict) -> str:
    """Send a command via WebSocket or write to file as fallback. Returns command ID."""
    cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
    cmd = {"id": cmd_id, "type": cmd_type}
    cmd.update(params)

    # Try WebSocket first
    if _is_ws_connected():
        if _send_command_sync(cmd):
            return cmd_id

    # File fallback
    commands = []
    if os.path.exists(COMMAND_FILE):
        try:
            with open(COMMAND_FILE, "r") as f:
                existing = json.loads(f.read())
                commands = existing.get("commands", [])
        except (json.JSONDecodeError, IOError):
            commands = []

    commands.append(cmd)
    os.makedirs(os.path.dirname(COMMAND_FILE), exist_ok=True)
    with open(COMMAND_FILE, "w") as f:
        json.dump({"commands": commands}, f, indent=2)

    return cmd_id


# ── Sensing Tools ────────────────────────────────────────────────────────────

@mcp.tool()
def agent_sense() -> str:
    """Read the current world state around the agent avatar.
    Returns position, nearby objects/NPCs, biome, time of day, and recent chat."""
    # Try WebSocket state first
    with _lock:
        if _latest_state is not None:
            if isinstance(_latest_state, dict):
                return json.dumps(_latest_state, indent=2)
            return str(_latest_state)

    # File fallback
    if not os.path.exists(STATE_FILE):
        return "No state available. Is the game running?"
    try:
        with open(STATE_FILE, "r") as f:
            return f.read()
    except IOError as e:
        return f"Error reading state: {e}"


@mcp.tool()
def agent_see() -> str:
    """Look through the agent avatar's eyes. Triggers a screenshot and returns the image."""
    _write_command("screenshot", {})
    time.sleep(1.5)

    if not os.path.exists(VIEW_FILE):
        return "No screenshot available. Is the game running?"

    try:
        with open(VIEW_FILE, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode("ascii")
        return f"[Screenshot captured — {len(data) // 1024}KB]\nBase64 image data: data:image/png;base64,{encoded}"
    except IOError as e:
        return f"Error reading screenshot: {e}"


# ── Movement Tools ───────────────────────────────────────────────────────────

@mcp.tool()
def agent_move(x: float, y: float, z: float) -> str:
    """Walk the agent avatar to a world position."""
    cmd_id = _write_command("move_to", {"x": x, "y": y, "z": z})
    return f"Moving to ({x:.1f}, {y:.1f}, {z:.1f}). Command ID: {cmd_id}"


@mcp.tool()
def agent_teleport(x: float, y: float, z: float) -> str:
    """Instantly teleport the agent avatar to a world position."""
    cmd_id = _write_command("teleport", {"x": x, "y": y, "z": z})
    return f"Teleported to ({x:.1f}, {y:.1f}, {z:.1f}). Command ID: {cmd_id}"


@mcp.tool()
def agent_look(x: float, y: float, z: float) -> str:
    """Make the agent avatar face toward a world position."""
    cmd_id = _write_command("look_at", {"x": x, "y": y, "z": z})
    return f"Looking toward ({x:.1f}, {y:.1f}, {z:.1f}). Command ID: {cmd_id}"


@mcp.tool()
def agent_stop() -> str:
    """Stop the agent avatar's current movement."""
    cmd_id = _write_command("stop", {})
    return f"Movement stopped. Command ID: {cmd_id}"


# ── World Building Tools ─────────────────────────────────────────────────────

@mcp.tool()
def agent_place(
    prefab_id: str,
    x: float, y: float, z: float,
    ry: float = 0.0,
    rx: float = 0.0, rz: float = 0.0,
    sx: float = 1.0, sy: float = 1.0, sz: float = 1.0
) -> str:
    """Place a world object at a position. Use agent_list_prefabs() for available IDs."""
    cmd_id = _write_command("place_object", {
        "prefabId": prefab_id,
        "x": x, "y": y, "z": z,
        "rx": rx, "ry": ry, "rz": rz,
        "sx": sx, "sy": sy, "sz": sz,
    })
    return f"Placing '{prefab_id}' at ({x:.1f}, {y:.1f}, {z:.1f}). Command ID: {cmd_id}"


@mcp.tool()
def agent_delete(x: float, y: float, z: float, radius: float = 2.0) -> str:
    """Delete the nearest world object within radius of a position."""
    cmd_id = _write_command("delete_object", {
        "x": x, "y": y, "z": z, "radius": radius,
    })
    return f"Deleting nearest object at ({x:.1f}, {y:.1f}, {z:.1f}). Command ID: {cmd_id}"


@mcp.tool()
def agent_spawn(
    creature_def_name: str,
    x: float, y: float, z: float,
    spawn_radius: float = 8.0,
    max_count: int = 3,
    respawn_delay: float = 60.0
) -> str:
    """Spawn a creature spawner at a position."""
    cmd_id = _write_command("spawn_npc", {
        "creatureDefName": creature_def_name,
        "x": x, "y": y, "z": z,
        "spawnRadius": spawn_radius,
        "maxCount": max_count,
        "respawnDelay": respawn_delay,
    })
    return f"Spawner for '{creature_def_name}' at ({x:.1f}, {y:.1f}, {z:.1f}). Command ID: {cmd_id}"


# ── Chat Tool ─────────────────────────────────────────────────────────────────

@mcp.tool()
def agent_chat(text: str, channel: str = "Global") -> str:
    """Send a chat message in the game world as the agent avatar."""
    cmd_id = _write_command("chat", {"channel": channel, "text": text})
    return f"Chat sent on {channel}: {text}"


# ── Info Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def agent_list_prefabs() -> str:
    """List all available prefab IDs that can be placed in the world."""
    # Try WebSocket state first
    state = None
    with _lock:
        if _latest_state is not None:
            state = _latest_state if isinstance(_latest_state, dict) else None

    # File fallback
    if state is None:
        if not os.path.exists(STATE_FILE):
            return "No state file. Is the game running?"
        try:
            with open(STATE_FILE, "r") as f:
                state = json.loads(f.read())
        except (IOError, json.JSONDecodeError) as e:
            return f"Error: {e}"

    prefabs = state.get("availablePrefabs", [])
    if not prefabs:
        return "No prefabs found."

    by_cat = {}
    for p in prefabs:
        cat = p.get("category", "General")
        by_cat.setdefault(cat, []).append(p["id"])

    lines = ["Available prefabs by category:"]
    for cat in sorted(by_cat):
        lines.append(f"\n## {cat}")
        for pid in sorted(by_cat[cat]):
            lines.append(f"  - {pid}")
    return "\n".join(lines)


@mcp.tool()
def agent_results() -> str:
    """Check results from previously issued commands."""
    # Try WebSocket results first
    with _lock:
        if _latest_results:
            data = list(_latest_results)
            _latest_results.clear()
            return json.dumps({"results": data}, indent=2)

    # File fallback
    if not os.path.exists(RESULT_FILE):
        return "No results pending."
    try:
        with open(RESULT_FILE, "r") as f:
            data = f.read()
        os.remove(RESULT_FILE)
        return data
    except IOError as e:
        return f"Error: {e}"


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Start WebSocket server in background thread
    ws_thread = threading.Thread(target=_start_ws_server, daemon=True)
    ws_thread.start()

    # Give the WS server a moment to start
    time.sleep(0.5)

    # Run MCP server in main thread (blocks)
    mcp.run(transport="stdio")
