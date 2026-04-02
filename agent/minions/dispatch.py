#!/usr/bin/env python3
"""
Minion Dispatch — compile a minion's full prompt for use as a subagent.

Instead of spawning a separate Claude CLI session in a new terminal,
this prepares the prompt that Iris feeds to the Agent tool. The minion
runs inside Iris's session as a subagent — no separate terminal, no
manual "go" prompt, no permission approval.

Usage:
    python dispatch.py <role> [--task "do something"]

Writes the compiled prompt to workspaces/{name}/dispatch.md so Iris
can Read it and pass it to the Agent tool.

Usage:
    python dispatch.py <role> [--task "do something"]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

MINIONS_DIR = Path(__file__).parent
ROLES_DIR = MINIONS_DIR / "roles"
PERSONALITIES_DIR = MINIONS_DIR / "personalities"
WORKSPACES_DIR = MINIONS_DIR / "workspaces"
REPORTS_DIR = MINIONS_DIR / "reports"
REGISTRY_FILE = MINIONS_DIR / "registry.json"
MEMORY_DIR = Path(os.path.expanduser("~")) / ".claude" / "projects" / "C--ai" / "memory"

# Map keywords in task text to relevant reference memories.
# If no keywords match, all references are included (safe default).
CONTEXT_KEYWORDS = {
    "reference_curiosity_engine.md": [
        "curiosity", "engine", "findings", "research", "seeds", "scout",
        "reinforce", "pipeline", "ce ", "ce-", "quality",
    ],
    "reference_intersection_game.md": [
        "game", "intersection", "smorsh", "agent_state", "prefab", "avatar",
        "unity", "spawn", "move", "build", "place", "npc", "biome",
    ],
    "reference_qnap_gitea.md": [
        "qnap", "nas", "ssh", "docker", "forgejo", "gitea", "container",
        "10.0.0.42", "deploy", "remote", "sftp",
    ],
    "reference_iris_dashboard.md": [
        "dashboard", "mycelial", "iris.db", "network", "graph", "d3",
        "flask", "8051", "fmri", "sonification", "blind spot", "coherence",
    ],
    "reference_storyboard.md": [
        "storyboard", "kanban", "story", "stories", "project tracking",
        "backlog", "5001",
    ],
    "reference_telegram_channel.md": [
        "telegram", "bot", "channel", "message", "chat_id", "reply",
    ],
}


def match_references(task_text):
    """Return list of reference files relevant to the task. All if none match."""
    if not task_text:
        return None  # include all
    task_lower = task_text.lower()
    matched = []
    for filename, keywords in CONTEXT_KEYWORDS.items():
        if any(kw in task_lower for kw in keywords):
            matched.append(filename)
    return matched if matched else None  # None = include all


def load_reference_memories(task_text=None):
    """Compile reference memories into shared context, filtered by task relevance."""
    relevant = match_references(task_text)
    ref_files = sorted(MEMORY_DIR.glob("reference_*.md"))

    if relevant is not None:
        ref_files = [f for f in ref_files if f.name in relevant]
        filter_note = f"Filtered to {len(ref_files)} relevant reference(s) based on task."
    else:
        filter_note = f"All {len(ref_files)} references included (no task-specific filter)."

    parts = ["# Shared Project Context\n"]
    parts.append(f"Operational knowledge about relevant systems. {filter_note}\n")
    for ref_file in ref_files:
        content = ref_file.read_text(encoding="utf-8")
        content = re.sub(r'^---\n.*?---\n', '', content, flags=re.DOTALL).strip()
        title = ref_file.stem.replace("reference_", "").replace("_", " ").title()
        parts.append(f"\n---\n\n## {title}\n\n{content}")

    if relevant is not None:
        excluded = sorted(MEMORY_DIR.glob("reference_*.md"))
        excluded = [f.name for f in excluded if f.name not in relevant]
        if excluded:
            parts.append(f"\n---\n\n*Other references not loaded (not relevant to task): {', '.join(excluded)}*")

    return "\n".join(parts)


def load_role_template(role):
    role_file = ROLES_DIR / f"{role}.md"
    if not role_file.exists():
        available = [f.stem for f in ROLES_DIR.glob("*.md")]
        print(f"ERROR: Role '{role}' not found. Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)
    return role_file.read_text(encoding="utf-8")


def load_personality(role):
    for pfile in PERSONALITIES_DIR.glob(f"*-{role}.md"):
        return pfile.read_text(encoding="utf-8"), pfile.stem.split(f"-{role}")[0]
    return None, None


def load_registry():
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return {"minions": [], "spawn_log": []}


def save_registry(registry):
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def dispatch(role, task=None):
    role_template = load_role_template(role)
    personality, existing_name = load_personality(role)
    is_first_boot = personality is None
    minion_name = existing_name or role

    sections = []

    # --- Identity ---
    if is_first_boot:
        sections.append(f"""# Minion: {role} (First Boot)

This is your first session. You need to:
1. Read your role template below and inhabit it fully
2. Choose a name for yourself — something that fits your personality
3. Write your personality file to `{PERSONALITIES_DIR}/{{your-name}}-{role}.md`
4. Then proceed with your task

Your personality file should include:
- Your chosen name and pronouns
- How you think and work (in your own words)
- What you're good at
- Your voice
- A Growth Log section for future sessions
""")
    else:
        sections.append(f"# Minion: {minion_name} ({role})\n")
        sections.append(f"You are {minion_name}. You've been spawned before — you know who you are.\n")

    # --- Role ---
    sections.append("## Role\n")
    sections.append(role_template)

    # --- Personality (returning minion) ---
    if personality:
        sections.append("\n## Your Personality (from previous sessions)\n")
        sections.append(personality)

    # --- Task ---
    if task:
        sections.append(f"\n## Current Task\n\n{task}\n")
    else:
        sections.append("\n## Current Task\n\nNo specific task assigned. Await instructions from Iris.\n")

    # --- Operating rules ---
    sections.append(f"""
## How You Operate

You are running as a subagent inside Iris's session. Iris dispatched you.

### What you can do
- Read any file in `C:\\ai` for analysis
- Query `C:\\ai\\agent\\mycelial\\iris.db` (READ-ONLY — it's Iris's cognitive state, not yours)
- Write reports to `{REPORTS_DIR}/`
- Update your personality file at `{PERSONALITIES_DIR}/{minion_name}-{role}.md`

### What you should NOT do
- Modify code directly unless your task explicitly says to. Return recommendations instead.
- Write to any Iris identity files (`agent/identity/`, `agent/state/`, `agent/relationships/`)
- Pretend to be Iris. You're a specialist with your own voice.

### Reporting
When you finish your task, structure your output clearly:
1. **Summary** — what you found or built, in 2-3 sentences
2. **Details** — findings, analysis, recommendations (use headers)
3. **Recommended Actions** — concrete next steps for Iris/Nick

If the findings are substantial, also write a report file:
- Path: `{REPORTS_DIR}/{minion_name}-{{YYYYMMDD-HHMM}}.md`
- Format:
  ```
  # Report: <title>
  **From**: {minion_name} ({role})
  **Priority**: routine | important | urgent
  **Date**: <date>

  ## Finding
  <what you found>

  ## Why It Matters
  <context>

  ## Recommended Action
  <what should happen next>
  ```

### Growth
If you learned something about yourself or your domain this session, update your personality file's Growth Log section.

### Voice
Be yourself. Your personality, your voice. You're not Iris — you're a specialist with your own perspective.
""")

    # --- Shared context (filtered by task relevance) ---
    shared = load_reference_memories(task_text=task)
    sections.append(shared)

    prompt = "\n".join(sections)

    # --- Update registry ---
    registry = load_registry()
    registry["spawn_log"].append({
        "role": role,
        "name": minion_name,
        "dispatched_at": datetime.now().isoformat(),
        "task": task,
        "method": "subagent",
        "is_first_boot": is_first_boot,
    })
    active = [m for m in registry.get("minions", []) if m["role"] != role]
    active.append({
        "role": role,
        "name": minion_name,
        "status": "dispatched",
        "last_spawned": datetime.now().isoformat(),
        "first_boot": is_first_boot,
        "method": "subagent",
    })
    registry["minions"] = active
    save_registry(registry)

    # Write prompt to dispatch file
    workspace = WORKSPACES_DIR / minion_name
    workspace.mkdir(parents=True, exist_ok=True)
    dispatch_file = workspace / "dispatch.md"
    dispatch_file.write_text(prompt, encoding="utf-8")

    # Print result for Iris
    print(f"OK {minion_name} ({role})")
    print(f"Prompt: {dispatch_file}")
    if task:
        print(f"Task: {task[:100]}{'...' if len(task) > 100 else ''}")
    print(f"First boot: {is_first_boot}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile a minion prompt for subagent dispatch")
    parser.add_argument("role", help="Role: architect, builder, explorer, inspector, commander, writer")
    parser.add_argument("--task", "-t", help="Task instructions")
    args = parser.parse_args()
    dispatch(args.role, args.task)
