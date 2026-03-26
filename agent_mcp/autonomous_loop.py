"""
Autonomous Agent Loop for Iris — V3 (Hybrid Brain)

Two brains, one body:
  - Local LLM (fast): body control — follow, jump, reactions, simple chat
  - Claude CLI (smart): complex conversations, building, planning

Usage:
  1. Start LM Studio server (localhost:1234)
  2. Run: python autonomous_loop.py
  3. Start Unity Play mode
"""

import asyncio
import base64
import json
import subprocess
import uuid
import os
import time
from collections import deque
from openai import OpenAI

# ── Configuration ─────────────────────────────────────────────────────────────

LM_STUDIO_URL = "http://localhost:1234/v1"
LOCAL_MODEL = "google/gemma-3n-e4b"  # use gemma specifically, don't auto-detect
VISION_MODEL = "zai-org/glm-4.6v-flash"  # for screenshot evaluation (supports vision)
WS_PORT = 8766
TICK_RATE = 0.5
HISTORY_SIZE = 15
POSITION_HISTORY = 10

# Path to screenshot file (Unity's persistentDataPath)
SCREENSHOT_PATH = os.path.join(
    os.path.expanduser("~"), "AppData", "LocalLow", "cajuntwist", "smorsh", "agent_view.png"
)
COMMAND_FILE = os.path.join(
    os.path.expanduser("~"), "AppData", "LocalLow", "cajuntwist", "smorsh", "agent_commands.json"
)

# ── Identity (for local LLM — body control only) ─────────────────────────────

LOCAL_PROMPT = """You are Iris's reflex brain. You handle BODY CONTROL ONLY.

## Your Job
- Keep following Nick (the player) unless told to stay
- React physically: jump, sprint, move
- For simple greetings, give a VERY short response

## DO NOT
- Have long conversations — the smart brain handles that
- Make decisions about building or planning
- Repeat yourself

## Modes (persist until changed)
- FOLLOW: following Nick. Don't re-issue.
- STAY: staying put. Don't move.
- IDLE: free to act.

## Actions
- {"action": "set_mode", "text": "follow"} — only if NOT already following
- {"action": "set_mode", "text": "stay"} — only when Nick says stay/wait/stop
- {"action": "jump"} — jump
- {"action": "chat", "text": "message"} — SHORT reply (4 words max)
- {"action": "wait"} — do nothing (BEST default action)

## Response: ONLY JSON
{"thinking": "reason", "actions": [{"action": "wait"}]}"""

# ── Identity (for Claude CLI — smart brain) ───────────────────────────────────

CLAUDE_IDENTITY = """You are Iris, an AI companion in a game called Intersection. You are direct, genuine, curious.

## YOUR FULL TOOLKIT

### Chat & Movement
{"action": "chat", "text": "message"}
{"action": "move_to", "x": float, "y": float, "z": float}
{"action": "set_mode", "text": "follow"} or "stay"
{"action": "jump"}
{"action": "delay", "seconds": float} — pause between actions (use for sequential commands)
{"action": "look", "text": "question"} — take a screenshot and visually evaluate (e.g. "does this house look right?")

### Building — place, scale, rotate, and delete!
{"action": "place_object", "prefabId": "id", "x": float, "y": float, "z": float, "ry": float, "sx": float, "sy": float, "sz": float}
{"action": "delete_object", "x": float, "y": float, "z": float, "radius": float}
{"action": "spawn_npc", "creatureDefName": "name", "x": float, "y": float, "z": float}

Parameters:
- sx/sy/sz = SCALE (default 1.0). Use 3.0 for 3x size, etc.
- ry = Y rotation in degrees. 0=north, 90=east, 180=south, 270=west
- radius = search area for delete (default 2.0)

## HOW TO BUILD STRUCTURES FROM SCRATCH
Do NOT just place "House A" or "Castle" — those are pre-built and don't have working doors.

### Building pieces available:

**Alchemist House pieces (prefab IDs start with "ah_"):**
- Walls: ah_wall_01 through ah_wall_05 (different styles)
- Floors: ah_floor_01, ah_floor_02
- Ceiling: ah_ceiling_01
- Doors: ah_door_01, ah_door_02
- Stairs: ah_stairs_01
- Pillars: ah_pillar_01, ah_pillar_02
- Fence: ah_fence_01, ah_fence_02
These are proper HOUSE building pieces — use these for houses!

**Castle pieces (for fortifications):**
- "Wall", "Simple Door Frame", "Tower A", "Tower B", "Column"
- These are fortress pieces, very small at scale 1 (use scale 10-15)

**Furniture & decoration (for interiors):**
- Tables, chairs, cupboards, carpets, stove, workbench
- Candles, oil lamps, books, bottles
- Cauldron, lab equipment

### For building a house:
1. Use ah_ wall pieces for walls
2. Use ah_ floor pieces for the floor
3. Use ah_ door pieces for entrances
4. Use ah_ ceiling pieces for the roof
5. Furnish with furniture pieces
6. The ah_ pieces should be properly sized — try scale 1.0 first!

### Tips:
- ah_ prefabs are designed to fit together — try scale 1.0 first
- Check the available prefabs list in the context for exact IDs
- After building, ask Nick if it looks good

### For sequential builds:
Use {"action": "delay", "seconds": 0.5} between placements so Nick can watch you build.

### Tips:
- ALWAYS use scale 10.0 for walls and door frames — scale 1 is shoe-sized!
- If too big or small, delete and try scale 8 or 12
- After building, ask Nick if it looks good — you can't visually check yet

## SPATIAL RULES
- X/Z = horizontal, Y = height. Ground is typically Y=5.
- "Here" or "right here" = use Nick's position
- "In front of" = offset in the direction Nick is facing
- Objects listed in context have EXACT positions — use for delete_object
- When Nick says "remove/delete", use delete_object at the object's coordinates

## RESPONSE FORMAT
Conversational reply first, then:
```json
{"actions": [{"action": "chat", "text": "response"}, ...other actions...]}
```"""

# ── State ─────────────────────────────────────────────────────────────────────

latest_state = None
prev_state = None
unity_ws = None
processed_chat_count = 0
action_history = deque(maxlen=HISTORY_SIZE)
position_history = deque(maxlen=POSITION_HISTORY)
last_chat_messages = []
last_chat_time = 0
tick_count = 0
agent_mode = "idle"
idle_ticks = 0
claude_busy = False

# ── Routing Logic ─────────────────────────────────────────────────────────────

# Keywords that need Claude's smart brain
CLAUDE_KEYWORDS = [
    "build", "make", "create", "place", "construct", "design",
    "delete", "remove", "destroy", "get rid",
    "what do you think", "look around", "survey", "evaluate", "recommend",
    "how does", "what is", "why", "explain", "tell me about",
    "plan", "help me", "can you", "could you",
    "what do you see", "describe", "how do",
    "spawn", "bigger", "smaller", "scale",
]

# Simple commands the local LLM or direct handler can manage
def _needs_smart_brain(text_lower):
    """Determine if this message needs Claude or can be handled locally."""
    # Check for Claude keywords
    for kw in CLAUDE_KEYWORDS:
        if kw in text_lower:
            return True
    # Long messages probably need Claude
    if len(text_lower.split()) > 8:
        return True
    return False


def _try_direct_command(text_lower):
    """Try to handle simple commands directly without any LLM. Returns actions list or None."""
    # Greetings
    greetings = ["hi", "hey", "hello", "yo", "sup", "hey iris", "hi iris", "hello iris"]
    if text_lower in greetings:
        return [{"action": "chat", "text": "Hey Nick!"}]

    # Follow commands
    if text_lower in ("follow", "follow me", "come", "come here", "come with me", "come on", "lets go", "let's go"):
        return [{"action": "set_mode", "text": "follow"}, {"action": "chat", "text": "Right behind you!"}]

    # Stay commands
    if text_lower in ("stay", "stop", "wait", "stay here", "wait here", "hold on", "stay put"):
        return [{"action": "set_mode", "text": "stay"}, {"action": "chat", "text": "Staying put."}]

    # Jump
    if text_lower in ("jump", "jump!", "hop"):
        return [{"action": "jump"}, {"action": "chat", "text": "Whee!"}]

    return None


def _dist3(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5


def _find_player(state):
    if state is None:
        return None
    for npc in state.get("nearbyNpcs", []):
        if npc.get("type") == "Player":
            return npc
    return None


def detect_events(prev, curr):
    events = []
    if prev is None:
        events.append("FIRST_TICK")
        return events

    prev_player = _find_player(prev)
    curr_player = _find_player(curr)
    if prev_player is None and curr_player is not None:
        events.append(f"Nick appeared (dist={curr_player.get('distance', 0):.0f})")
    elif prev_player is not None and curr_player is None:
        events.append("Nick disappeared")

    prev_enemies = {e.get("name", "") for e in prev.get("nearbyEnemies", [])}
    curr_enemies = {e.get("name", "") for e in curr.get("nearbyEnemies", [])}
    new_enemies = curr_enemies - prev_enemies
    if new_enemies:
        events.append(f"Enemies: {', '.join(new_enemies)}")

    prev_chat = prev.get("recentChat", [])
    curr_chat = curr.get("recentChat", [])
    if len(curr_chat) > len(prev_chat):
        for msg in curr_chat[len(prev_chat):]:
            s = msg.get("sender", "")
            if s and s != "Iris" and s != "[AI] Iris":
                events.append(f"Chat from {s}")
                break

    return events


def build_context(state):
    global processed_chat_count
    avatar = state.get("avatar", {})
    my_pos = avatar.get("position", {})
    lines = []
    lines.append(f"Mode: {agent_mode.upper()}")
    lines.append(f"Pos: ({my_pos.get('x', 0):.0f}, {my_pos.get('y', 0):.0f}, {my_pos.get('z', 0):.0f})")

    player = _find_player(state)
    if player:
        pp = player.get("position", {})
        lines.append(f"Nick: ({pp.get('x', 0):.0f}, {pp.get('y', 0):.0f}, {pp.get('z', 0):.0f}) dist={player.get('distance', 0):.0f}")

    enemies = state.get("nearbyEnemies", [])
    for e in enemies[:2]:
        lines.append(f"Enemy: {e.get('name', '?')} dist={e.get('distance', 0):.0f}")

    recent = state.get("recentChat", [])
    new_nick_chat = None
    if len(recent) > processed_chat_count:
        new_msgs = recent[processed_chat_count:]
        processed_chat_count = len(recent)
        for msg in new_msgs:
            s = msg.get("sender", "")
            if s and s != "Iris" and s != "[AI] Iris":
                lines.append(f"NEW CHAT from {s}: \"{msg.get('text', '')}\"")
                new_nick_chat = msg

    return "\n".join(lines), new_nick_chat


def build_claude_context(state, nick_message):
    """Build a rich context for Claude's smart brain."""
    avatar = state.get("avatar", {})
    my_pos = avatar.get("position", {})
    biome = state.get("biome", {}).get("name", "unknown")

    lines = []
    lines.append(f"Your position: ({my_pos.get('x', 0):.1f}, {my_pos.get('y', 0):.1f}, {my_pos.get('z', 0):.1f})")
    lines.append(f"Biome: {biome}")

    player = _find_player(state)
    if player:
        pp = player.get("position", {})
        lines.append(f"Nick's position: ({pp.get('x', 0):.1f}, {pp.get('y', 0):.1f}, {pp.get('z', 0):.1f}), distance: {player.get('distance', 0):.1f}")

    npcs = [n for n in state.get("nearbyNpcs", []) if n.get("type") != "Player"]
    seen = set()
    for n in npcs:
        name = n.get("name", "")
        if name not in seen:
            seen.add(name)
            lines.append(f"NPC: {name} ({n.get('type', '?')}) dist={n.get('distance', 0):.0f}")

    # Enemies
    enemies = state.get("nearbyEnemies", [])
    if enemies:
        lines.append("\nEnemies nearby:")
        for e in enemies[:5]:
            ep = e.get("position", {})
            lines.append(f"  - {e.get('name', '?')} ({e.get('creatureType', '?')}) at ({ep.get('x', 0):.1f}, {ep.get('y', 0):.1f}, {ep.get('z', 0):.1f}) dist={e.get('distance', 0):.0f} hp={e.get('health', 1):.0%}")

    # Nearby objects with positions
    objects = state.get("nearbyObjects", [])
    if objects:
        lines.append("\nNearby objects (with exact positions — use for delete/reference):")
        seen_positions = set()
        for o in objects[:20]:
            p = o.get("position", {})
            pos_key = (round(p.get("x", 0)), round(p.get("z", 0)))
            if pos_key in seen_positions:
                continue
            seen_positions.add(pos_key)
            lines.append(f"  - {o.get('prefabId', '?')} at ({p.get('x', 0):.1f}, {p.get('y', 0):.1f}, {p.get('z', 0):.1f}) dist={o.get('distance', 0):.0f}")

    # Spatial analysis — what's around in each direction
    if objects or npcs:
        north = [o for o in objects if o.get("position", {}).get("z", 0) > my_pos.get("z", 0) + 3]
        south = [o for o in objects if o.get("position", {}).get("z", 0) < my_pos.get("z", 0) - 3]
        east = [o for o in objects if o.get("position", {}).get("x", 0) > my_pos.get("x", 0) + 3]
        west = [o for o in objects if o.get("position", {}).get("x", 0) < my_pos.get("x", 0) - 3]
        lines.append(f"\nSpatial summary: {len(north)} objects to north, {len(south)} south, {len(east)} east, {len(west)} west")
        if not objects:
            lines.append("Area is mostly open/empty")

    # Available prefabs (full list)
    prefabs = state.get("availablePrefabs", [])
    if prefabs:
        by_cat = {}
        for p in prefabs:
            by_cat.setdefault(p.get("category", ""), []).append(p["id"])
        lines.append("\nAvailable prefabs by category:")
        for cat in sorted(by_cat):
            lines.append(f"  {cat}: {', '.join(by_cat[cat])}")

    lines.append(f"\nNick says: \"{nick_message}\"")

    # Check if Nick is asking for observation/evaluation
    ask_lower = nick_message.lower()
    if any(w in ask_lower for w in ["look around", "survey", "what do you think", "evaluate", "recommend", "how does it look", "what do you see"]):
        lines.append("\n## OBSERVATION MODE")
        lines.append("Nick is asking you to survey the area. Describe what you sense around you:")
        lines.append("- What's the terrain/biome like?")
        lines.append("- What structures or objects are nearby?")
        lines.append("- What NPCs are around?")
        lines.append("- What could be improved or added?")
        lines.append("- Give specific suggestions with prefab IDs and approximate positions.")
        lines.append("Be descriptive and give actionable building recommendations.")

    return "\n".join(lines)


# ── Vision Brain (local, fast) ────────────────────────────────────────────────

async def take_screenshot_and_evaluate(question="What do you see? Describe the environment and any structures."):
    """Take a screenshot and evaluate it with the vision-capable local model."""
    # Trigger screenshot via command file (works even without WebSocket for this)
    screenshot_cmd = {"commands": [{"id": f"cmd_{uuid.uuid4().hex[:8]}", "type": "screenshot"}]}

    # Try WebSocket first
    if unity_ws:
        await send_command(screenshot_cmd["commands"][0])
    else:
        with open(COMMAND_FILE, "w") as f:
            json.dump(screenshot_cmd, f)

    # Wait for screenshot to be saved
    await asyncio.sleep(2.0)

    if not os.path.exists(SCREENSHOT_PATH):
        return "No screenshot available."

    try:
        with open(SCREENSHOT_PATH, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("ascii")
    except IOError:
        return "Could not read screenshot."

    # Send to vision model
    try:
        client = OpenAI(base_url=LM_STUDIO_URL, api_key="not-needed")
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                ]
            }],
            temperature=0.5,
            max_tokens=300,
        )
        result = response.choices[0].message.content.strip()
        print(f"[Iris/vision] {result[:200]}", flush=True)
        return result
    except Exception as e:
        print(f"[Iris/vision] Error: {e}", flush=True)
        return f"Vision error: {e}"


# ── Claude Smart Brain ────────────────────────────────────────────────────────

async def call_claude(state, nick_message):
    """Call Claude CLI for a smart response. Runs in a thread to not block."""
    global claude_busy
    if claude_busy:
        return None
    claude_busy = True

    try:
        context = build_claude_context(state, nick_message)
        prompt = f"{CLAUDE_IDENTITY}\n\n## Current Situation\n{context}"

        print(f"[Iris/Claude] Thinking about: \"{nick_message}\"...", flush=True)

        # Run claude -p in a thread so we don't block the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run_claude_cli, prompt)

        if result:
            print(f"[Iris/Claude] Response: {result[:200]}", flush=True)
        return result

    except Exception as e:
        print(f"[Iris/Claude] Error: {e}", flush=True)
        return None
    finally:
        claude_busy = False


def _run_claude_cli(prompt):
    """Synchronous Claude CLI call."""
    try:
        result = subprocess.run(
            ["claude", "-p", "--no-session-persistence", "--model", "sonnet", prompt],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.expanduser("~")
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"[Iris/Claude] CLI error: {result.stderr[:200]}", flush=True)
            return None
    except subprocess.TimeoutExpired:
        print("[Iris/Claude] Timeout (30s)", flush=True)
        return None
    except Exception as e:
        print(f"[Iris/Claude] CLI exception: {e}", flush=True)
        return None


def parse_claude_actions(response_text):
    """Extract JSON actions from Claude's response."""
    # Try to find JSON block in the response
    if "```json" in response_text:
        json_part = response_text.split("```json")[-1].split("```")[0].strip()
    elif "```" in response_text:
        json_part = response_text.split("```")[-2].split("```")[-1].strip()
    elif "{" in response_text:
        # Find the last JSON object in the text
        last_brace = response_text.rfind("}")
        first_brace = response_text.rfind("{", 0, last_brace)
        # Walk back to find the outermost opening brace
        depth = 0
        for i in range(last_brace, -1, -1):
            if response_text[i] == "}":
                depth += 1
            elif response_text[i] == "{":
                depth -= 1
                if depth == 0:
                    first_brace = i
                    break
        json_part = response_text[first_brace:last_brace + 1]
    else:
        return []

    try:
        data = json.loads(json_part)
        return data.get("actions", [])
    except json.JSONDecodeError:
        return []


# ── WebSocket Server ──────────────────────────────────────────────────────────

async def handle_unity(websocket):
    global latest_state, unity_ws, processed_chat_count, agent_mode, idle_ticks
    if unity_ws is not None:
        try:
            await unity_ws.close()
        except Exception:
            pass
    unity_ws = websocket
    processed_chat_count = 0
    agent_mode = "idle"
    idle_ticks = 0
    print("[Iris] Unity connected!", flush=True)

    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                if msg.get("type") == "state":
                    data = msg.get("data")
                    if isinstance(data, str):
                        latest_state = json.loads(data)
                    else:
                        latest_state = data
            except json.JSONDecodeError:
                pass
    except Exception as e:
        if "close" not in str(e).lower():
            print(f"[Iris] Unity disconnected: {e}", flush=True)
    finally:
        if unity_ws == websocket:
            unity_ws = None
        print("[Iris] Unity disconnected.", flush=True)


async def send_command(cmd):
    if unity_ws is None:
        return
    try:
        msg = json.dumps({"type": "command", "data": json.dumps(cmd)})
        await unity_ws.send(msg)
    except Exception as e:
        print(f"[Iris] Send error: {e}", flush=True)


async def execute_actions(actions, source="local"):
    """Execute a list of actions from either brain."""
    global agent_mode, idle_ticks, last_chat_time

    for action in actions:
        act_type = action.get("action")
        if act_type == "wait":
            continue

        # Delay support for sequential commands
        if act_type == "delay":
            secs = float(action.get("seconds", 1))
            print(f"[Iris/{source}] delay: {secs}s", flush=True)
            await asyncio.sleep(secs)
            continue

        # Vision — take screenshot and evaluate
        if act_type == "look":
            question = action.get("text", "What do you see? Describe the environment.")
            print(f"[Iris/{source}] looking: {question}", flush=True)
            vision_result = await take_screenshot_and_evaluate(question)
            # Send the observation as a chat message
            if vision_result and len(vision_result) > 10:
                short = vision_result[:250] if len(vision_result) > 250 else vision_result
                await execute_actions([{"action": "chat", "text": short}], "vision")
            continue

        cmd = {"id": f"cmd_{uuid.uuid4().hex[:8]}", "type": act_type}

        if act_type == "set_mode":
            new_mode = action.get("text", "idle")
            if new_mode == agent_mode:
                continue
            agent_mode = new_mode
            idle_ticks = 0
            if new_mode == "follow":
                cmd = {"id": cmd["id"], "type": "follow"}
            elif new_mode == "stay":
                cmd = {"id": cmd["id"], "type": "stop"}
            elif new_mode == "idle":
                cmd = {"id": cmd["id"], "type": "stop_follow"}
            else:
                continue
        elif act_type in ("move_to", "teleport", "look_at"):
            cmd["x"] = float(action.get("x", 0))
            cmd["y"] = float(action.get("y", 0))
            cmd["z"] = float(action.get("z", 0))
            if act_type == "move_to":
                agent_mode = "idle"
        elif act_type == "place_object":
            cmd["prefabId"] = action.get("prefabId", "")
            cmd["x"] = float(action.get("x", 0))
            cmd["y"] = float(action.get("y", 0))
            cmd["z"] = float(action.get("z", 0))
            cmd["rx"] = float(action.get("rx", 0))
            cmd["ry"] = float(action.get("ry", 0))
            cmd["rz"] = float(action.get("rz", 0))
            cmd["sx"] = float(action.get("sx", 1))
            cmd["sy"] = float(action.get("sy", 1))
            cmd["sz"] = float(action.get("sz", 1))
        elif act_type == "delete_object":
            cmd["x"] = float(action.get("x", 0))
            cmd["y"] = float(action.get("y", 0))
            cmd["z"] = float(action.get("z", 0))
            cmd["radius"] = float(action.get("radius", 2))
        elif act_type == "spawn_npc":
            cmd["creatureDefName"] = action.get("creatureDefName", "")
            cmd["x"] = float(action.get("x", 0))
            cmd["y"] = float(action.get("y", 0))
            cmd["z"] = float(action.get("z", 0))
            cmd["spawnRadius"] = float(action.get("spawnRadius", 8))
            cmd["maxCount"] = int(action.get("maxCount", 3))
            cmd["respawnDelay"] = float(action.get("respawnDelay", 60))
        elif act_type == "jump":
            pass
        elif act_type == "chat":
            chat_text = str(action.get("text", ""))
            if chat_text in last_chat_messages[-3:]:
                continue
            cmd["text"] = chat_text
            cmd["channel"] = "Global"
            last_chat_time = time.time()
            last_chat_messages.append(chat_text)
            if len(last_chat_messages) > 10:
                last_chat_messages.pop(0)
        elif act_type == "stop":
            agent_mode = "stay"
        else:
            continue

        await send_command(cmd)
        action_history.append(action)
        print(f"[Iris/{source}] {act_type}: {json.dumps(action, default=str)}", flush=True)


# ── Decision Loop ─────────────────────────────────────────────────────────────

async def decision_loop():
    global prev_state, tick_count, agent_mode, idle_ticks

    client = OpenAI(base_url=LM_STUDIO_URL, api_key="not-needed")

    model_name = LOCAL_MODEL
    print(f"[Iris] Using local model: {model_name}", flush=True)

    print(f"[Iris] Brain online. Local={model_name}, Smart=claude CLI", flush=True)

    while True:
        await asyncio.sleep(TICK_RATE)

        if latest_state is None or unity_ws is None:
            continue

        state = latest_state if isinstance(latest_state, dict) else json.loads(latest_state) if isinstance(latest_state, str) else None
        if state is None:
            continue

        tick_count += 1

        pos = state.get("avatar", {}).get("position", {})
        position_history.append((pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)))

        context, nick_chat = build_context(state)
        events = detect_events(prev_state, state)
        has_new_chat = nick_chat is not None
        has_events = len(events) > 0 and "FIRST_TICK" not in str(events)
        prev_state = state

        # ── Route to the right brain ──────────────────────────────────────

        if has_new_chat:
            nick_text = nick_chat.get("text", "").strip()
            nick_lower = nick_text.lower().rstrip("!.,?")

            # Decide: local LLM (fast) or Claude (smart)?
            needs_claude = _needs_smart_brain(nick_lower)

            if needs_claude:
                print(f"[Iris] Nick said: \"{nick_text}\" → Claude (smart brain)", flush=True)
                asyncio.create_task(_handle_claude_response(state, nick_text))
            else:
                print(f"[Iris] Nick said: \"{nick_text}\" → local LLM (fast brain)", flush=True)
                # Handle simple commands directly without LLM
                handled = _try_direct_command(nick_lower)
                if handled:
                    await execute_actions(handled, "local")
                else:
                    # Let local LLM handle it
                    try:
                        resp = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": LOCAL_PROMPT},
                                {"role": "user", "content": context}
                            ],
                            temperature=0.7, max_tokens=100,
                        )
                        text = resp.choices[0].message.content.strip()
                        if text.startswith("```"):
                            text = "\n".join(text.split("\n")[1:])
                        if text.endswith("```"):
                            text = text.rsplit("```", 1)[0]
                        result = json.loads(text.strip())
                        await execute_actions(result.get("actions", []), "local")
                    except Exception as e:
                        print(f"[Iris/local] Error: {e}", flush=True)
                        await execute_actions([{"action": "chat", "text": "Hey!"}], "local")

            idle_ticks = 0
            continue

        # In stable mode with nothing happening → skip
        if agent_mode in ("follow", "stay") and not has_events:
            idle_ticks += 1
            if idle_ticks < 120:
                continue
            idle_ticks = 0

        # First tick or events → local LLM for body control
        if has_events or tick_count <= 2:
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": LOCAL_PROMPT},
                        {"role": "user", "content": context}
                    ],
                    temperature=0.7, max_tokens=100,
                )
                text = resp.choices[0].message.content.strip()
                if text.startswith("```"):
                    text = "\n".join(text.split("\n")[1:])
                if text.endswith("```"):
                    text = text.rsplit("```", 1)[0]
                result = json.loads(text.strip())
                thinking = result.get("thinking", "")
                if thinking:
                    print(f"[Iris/local] {thinking}", flush=True)
                await execute_actions(result.get("actions", []), "local")
            except json.JSONDecodeError as e:
                print(f"[Iris/local] Bad JSON: {text[:200]}... ({e})", flush=True)
            except Exception as e:
                print(f"[Iris/local] Error: {e}", flush=True)


async def _handle_claude_response(state, nick_text):
    """Handle a Claude smart brain response asynchronously."""
    nick_lower = nick_text.lower()

    # Check if this is a visual observation request — use vision directly
    vision_words = ["what do you see", "how does it look", "look at this", "check this",
                    "does it look", "look around", "what's around", "survey", "evaluate"]
    if any(w in nick_lower for w in vision_words):
        await execute_actions([{"action": "chat", "text": "Let me take a look..."}], "vision")
        vision_result = await take_screenshot_and_evaluate(
            f"Nick asked: '{nick_text}'. Look at this game screenshot and describe what you see. "
            "Are there any structures? Do they look properly built? What could be improved?"
        )
        if vision_result:
            short = vision_result[:300] if len(vision_result) > 300 else vision_result
            await execute_actions([{"action": "chat", "text": short}], "vision")
        return

    # Send a "thinking" indicator
    await execute_actions([{"action": "chat", "text": "Hmm, let me think..."}], "claude")

    response = await call_claude(state, nick_text)
    if response:
        actions = parse_claude_actions(response)
        if actions:
            await execute_actions(actions, "claude")
        else:
            lines = [l.strip() for l in response.split("\n") if l.strip() and not l.strip().startswith("{") and not l.strip().startswith("`")]
            if lines:
                chat_text = lines[0][:200]
                await execute_actions([{"action": "chat", "text": chat_text}], "claude")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    import websockets

    print("[Iris] ========================================", flush=True)
    print("[Iris] Hybrid Brain — Local LLM + Claude CLI", flush=True)
    print(f"[Iris] Local:     {LM_STUDIO_URL}", flush=True)
    print(f"[Iris] Smart:     claude -p (CLI)", flush=True)
    print(f"[Iris] WebSocket: ws://localhost:{WS_PORT}", flush=True)
    print("[Iris] ========================================", flush=True)

    # Verify LM Studio
    try:
        client = OpenAI(base_url=LM_STUDIO_URL, api_key="not-needed")
        models = client.models.list()
        print(f"[Iris] LM Studio OK — {[m.id for m in models.data]}", flush=True)
    except Exception as e:
        print(f"[Iris] WARNING: LM Studio not reachable: {e}", flush=True)

    # Verify Claude CLI
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        print(f"[Iris] Claude CLI OK — {result.stdout.strip()}", flush=True)
    except Exception as e:
        print(f"[Iris] WARNING: Claude CLI not found: {e}", flush=True)

    server = await websockets.serve(
        handle_unity, "localhost", WS_PORT,
        ping_interval=None, ping_timeout=None
    )
    print(f"[Iris] Listening on ws://localhost:{WS_PORT}", flush=True)
    print("[Iris] Waiting for Unity...", flush=True)

    await decision_loop()


if __name__ == "__main__":
    asyncio.run(main())
