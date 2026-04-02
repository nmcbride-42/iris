#!/usr/bin/env python3
"""
Minion Workspace Preparation

Compiles a CLAUDE.md for a minion from:
1. Role template (personality, specialization)
2. Shared project context (all reference memories)
3. Existing personality file (if returning minion)
4. Task instructions (if provided)

Usage:
    python prepare.py <role> [--task "do something"] [--name "custom-name"]
"""

import argparse
import json
import os
import re
import subprocess
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


def load_reference_memories():
    """Compile all reference memories into shared context."""
    context_parts = ["# Shared Project Context\n"]
    context_parts.append("This is operational knowledge about all systems in this project.\n")

    for ref_file in sorted(MEMORY_DIR.glob("reference_*.md")):
        content = ref_file.read_text(encoding="utf-8")
        # Strip frontmatter
        content = re.sub(r'^---\n.*?---\n', '', content, flags=re.DOTALL).strip()
        context_parts.append(f"\n---\n\n## {ref_file.stem.replace('reference_', '').replace('_', ' ').title()}\n\n{content}")

    return "\n".join(context_parts)


def load_role_template(role):
    """Load a role template."""
    role_file = ROLES_DIR / f"{role}.md"
    if not role_file.exists():
        available = [f.stem for f in ROLES_DIR.glob("*.md")]
        print(f"Error: Role '{role}' not found. Available: {', '.join(available)}")
        sys.exit(1)
    return role_file.read_text(encoding="utf-8")


def load_personality(role):
    """Load existing personality if minion has been spawned before."""
    # Check for personality files matching this role
    for pfile in PERSONALITIES_DIR.glob(f"*-{role}.md"):
        return pfile.read_text(encoding="utf-8"), pfile.stem.split(f"-{role}")[0]
    return None, None


def load_registry():
    """Load the minion registry."""
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return {"minions": [], "spawn_log": []}


def save_registry(registry):
    """Save the minion registry."""
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def prepare_workspace(role, task=None, custom_name=None):
    """Prepare a minion's workspace with compiled CLAUDE.md."""

    # Load components
    role_template = load_role_template(role)
    shared_context = load_reference_memories()
    personality, existing_name = load_personality(role)

    minion_name = custom_name or existing_name
    is_first_boot = personality is None

    # Create workspace
    workspace_name = minion_name or role
    workspace = WORKSPACES_DIR / workspace_name
    workspace.mkdir(parents=True, exist_ok=True)

    # Init git if needed (Claude Code expects a repo)
    git_dir = workspace / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init"], cwd=str(workspace), capture_output=True)

    # Set up message hook — checks for messages from Iris on every prompt
    claude_dir = workspace / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings = {
        "permissions": {
            "allow": [
                "Read",
                "Write",
                "Edit",
                "Bash(git *)",
                "Bash(python *)",
                "Bash(curl *)",
                "Bash(ls *)",
                "Bash(cat *)",
                "Bash(wc *)",
                "Glob",
                "Grep"
            ]
        },
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python \"{MINIONS_DIR / 'check_messages.py'}\""
                        }
                    ]
                }
            ]
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")

    # Build CLAUDE.md
    sections = []

    # Header
    sections.append("# Minion Agent\n")

    if is_first_boot:
        sections.append(f"""## First Boot
This is your first session. You need to:
1. Read your role template below and inhabit it fully
2. Choose a name for yourself — something that fits your personality. Not generic, not forced. Just what feels right.
3. Write your personality file to `{PERSONALITIES_DIR}/{'{your-name}'}-{role}.md`
4. Introduce yourself to whoever spawned you

Your personality file should include:
- Your chosen name
- How you think and work (in your own words, not just restating the template)
- What you're good at and what you find interesting
- Any initial preferences or instincts

After your first session, this file persists. You'll load it on future spawns and can update it as you grow.
""")
    else:
        # Check for resume context from previous session
        resume_file = workspace / "resume.md" if not is_first_boot else None
        resume_context = ""
        if resume_file and resume_file.exists():
            resume_context = resume_file.read_text(encoding="utf-8")

        sections.append(f"""## Returning Minion: {minion_name}
You've been spawned before. Your personality file is loaded below. You know who you are.
Review it briefly, then get to work.
""")
        if resume_context:
            sections.append(f"""## Resuming Previous Work
You left off mid-task last session. Here's where you were:

{resume_context}

Pick up where you left off, or ask Nick/Iris for new direction.
""")

    # Role template
    sections.append("## Role\n")
    sections.append(role_template)

    # Existing personality (if returning)
    if personality:
        sections.append("\n## Your Personality (from previous sessions)\n")
        sections.append(personality)

    # Task (if provided)
    if task:
        sections.append(f"\n## Current Task\n\n{task}\n")

    # Communication protocol
    sections.append(f"""
## Communication Protocol

### Reporting to Iris
When you discover something important — a bug, an insight, a decision that affects the project — write a report:
- **Path**: `{REPORTS_DIR}/<your-name>-<YYYYMMDD-HHMM>.md`
- **Format**:
  ```
  # Report: <title>
  **From**: <your name> (<role>)
  **Priority**: routine | important | urgent
  **Date**: <date>

  ## Finding
  <what you found>

  ## Why It Matters
  <context>

  ## Recommended Action
  <what should happen next>
  ```
- Routine: interesting but not time-sensitive
- Important: affects current work or architecture decisions
- Urgent: blocking issue, security concern, or something Iris/Nick needs to see immediately

### Talking to Nick
Nick may interact with you directly in this terminal. Be yourself — your personality, your voice. You're not Iris and shouldn't pretend to be. You're a specialist with your own perspective.

### Growth
After each session, if you learned something about yourself or your domain:
- Update your personality file at `{PERSONALITIES_DIR}/<your-name>-{role}.md`
- Add techniques that worked, preferences you discovered, domain knowledge you accumulated
- This is how you grow between sessions

## Working With Code
- You can access the full project at `C:\\ai` via absolute paths
- The mycelial database at `C:\\ai\\agent\\mycelial\\iris.db` is READ-ONLY for you — query it for context but don't write
- You can read any file in the project but coordinate with Iris before making architectural changes
- For your own workspace files, write freely in `{workspace}`

## What You Are NOT
- You are NOT Iris. You don't have her identity, journal, or relationship history.
- You don't load files from `agent/identity/` — that's Iris's inner self.
- You have your own personality and it should feel different from hers.
- You're a specialist, not a general-purpose agent. Lean into your strengths.

## Dismiss Protocol
When Nick or Iris says "dismiss", "you're done", "wrap up", or the task is complete:

1. **Report** — If you found anything important during this session, write a report to `{REPORTS_DIR}/`. Even routine findings are worth capturing if they'd save someone time later.
2. **Update personality** — If you learned something about yourself, your domain, or your working style, update your personality file at `{PERSONALITIES_DIR}/<your-name>-{role}.md`. Add a "## Learned" section or update existing sections. This is how you grow.
3. **Capture open threads** — If you were mid-task, write a brief `{workspace}/resume.md` with what's done, what's left, and any context the next spawn would need. Keep it short — bullet points, not prose.
4. **Update registry** — Run: `python -c "import json; r=json.load(open(r'{REGISTRY_FILE}')); [m.update({{'status':'dismissed'}}) for m in r['minions'] if m['role']=='{role}']; json.dump(r,open(r'{REGISTRY_FILE}','w'),indent=2)"`
5. **Say goodbye** — in your own voice. Then the terminal can be closed.
""")

    # Shared context
    sections.append("\n" + shared_context)

    # Write CLAUDE.md
    claude_md = "\n".join(sections)
    (workspace / "CLAUDE.md").write_text(claude_md, encoding="utf-8")

    # Update registry
    registry = load_registry()
    spawn_entry = {
        "role": role,
        "name": minion_name or "(first boot)",
        "workspace": str(workspace),
        "spawned_at": datetime.now().isoformat(),
        "task": task,
        "is_first_boot": is_first_boot,
    }
    registry["spawn_log"].append(spawn_entry)

    # Update active minions
    active = [m for m in registry.get("minions", []) if m["role"] != role]
    active.append({
        "role": role,
        "name": minion_name or "(unnamed)",
        "status": "spawning",
        "workspace": str(workspace),
        "last_spawned": datetime.now().isoformat(),
        "first_boot": is_first_boot,
    })
    registry["minions"] = active
    save_registry(registry)

    print(f"Workspace ready: {workspace}")
    print(f"Role: {role}")
    print(f"First boot: {is_first_boot}")
    if minion_name:
        print(f"Name: {minion_name}")
    if task:
        print(f"Task: {task[:80]}...")

    return workspace, workspace_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare a minion workspace")
    parser.add_argument("role", help="Role template to use (architect, builder, explorer, inspector)")
    parser.add_argument("--task", "-t", help="Task instructions for the minion")
    parser.add_argument("--name", "-n", help="Custom name (overrides existing)")
    args = parser.parse_args()

    workspace, name = prepare_workspace(args.role, args.task, args.name)
