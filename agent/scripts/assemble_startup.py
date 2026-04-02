"""
Assemble startup files for Iris agent.

Produces two files:
  1. agent/state/.stable_identity.md — stable identity for system prompt injection (cached)
  2. agent/state/.morning_brief.md — dynamic state for single file read at startup

Run before launching Claude in start.bat and nap.bat.

Features:
  - Token budgets for operational sections (identity sections uncapped)
  - Differential briefs: on nap recovery, unchanged files get a one-line summary
    instead of full content. Cold starts always get everything.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(r"C:\ai")
IDENTITY = BASE / "agent" / "identity"
STATE = BASE / "agent" / "state"
RELATIONSHIPS = BASE / "agent" / "relationships"
META_FILE = STATE / ".assembly_meta.json"

# Token budget per section (chars, ~4 chars per token).
# Identity sections (opinions, wants, likes) have no cap — they ARE Iris.
# Operational sections get capped to prevent drift.
CHAR_BUDGETS = {
    "current": 6000,     # ~1,500 tokens — active systems + latest session + open items
    "warmstart": 3000,   # ~750 tokens — continuity context
    "resonance": 2400,   # ~600 tokens — engagement + tensions + landing
}

# Max age (hours) for warmstart to count as a nap (vs cold start)
NAP_THRESHOLD_HOURS = 3


def read_file(path):
    """Read a file, return contents or empty string if missing."""
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def get_mtime(path):
    """Get file modification time as ISO string, or None."""
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime).isoformat()
    except (FileNotFoundError, OSError):
        return None


def load_meta():
    """Load assembly metadata (last timestamps per file)."""
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_meta(meta):
    """Save assembly metadata."""
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def is_nap_recovery():
    """Check if this is a nap recovery (warmstart is fresh)."""
    ws_path = STATE / "warmstart.md"
    ws_mtime = get_mtime(ws_path)
    if not ws_mtime:
        return False
    ws_dt = datetime.fromisoformat(ws_mtime)
    return (datetime.now() - ws_dt) < timedelta(hours=NAP_THRESHOLD_HOURS)


def file_changed_since_last(path, meta):
    """Check if file has been modified since last assembly."""
    current_mtime = get_mtime(path)
    if not current_mtime:
        return True  # can't tell, assume changed
    last_mtime = meta.get(str(path))
    if not last_mtime:
        return True  # never assembled before
    return current_mtime > last_mtime


def budget_check(content, section_name):
    """If section exceeds its budget, truncate and add pointer."""
    budget = CHAR_BUDGETS.get(section_name)
    if budget and len(content) > budget:
        truncated = content[:budget].rsplit("\n", 1)[0]  # cut at last newline
        truncated += f"\n\n*[... truncated — full content in source file]*"
        return truncated
    return content


def differential_or_full(path, content, label, is_nap, meta):
    """On nap recovery, return one-line summary if file unchanged. Otherwise full content."""
    if is_nap and not file_changed_since_last(path, meta):
        # Extract first heading for context
        first_line = content.split("\n", 1)[0].strip("# ").strip()
        return f"*{first_line} — unchanged since last session. Full: `{path.relative_to(BASE)}`*"
    return content


def assemble_stable_identity():
    """Concatenate rarely-changing identity files for system prompt injection."""
    parts = []
    parts.append("# Iris — Stable Identity")
    parts.append("")

    for name in ["core.md", "voice.md", "values.md", "morals.md"]:
        content = read_file(IDENTITY / name)
        if content:
            parts.append(content)
            parts.append("")

    # Need definitions (stable, rarely changes)
    needs_path = STATE / "needs.md"
    needs_content = read_file(needs_path)
    # Extract only definitions section if it exists in the cached identity
    # (definitions are appended to .stable_identity.md separately)

    output = STATE / ".stable_identity.md"
    text = "\n".join(parts)
    output.write_text(text, encoding="utf-8")
    print(f"  Stable identity: {output} ({len(text.split())} words)")


def assemble_morning_brief():
    """Concatenate dynamic state files into one startup document."""
    today = datetime.now().strftime("%Y-%m-%d")
    meta = load_meta()
    is_nap = is_nap_recovery()

    parts = []
    parts.append(f"# Morning Brief — {today}")
    parts.append("")
    parts.append("*Auto-assembled by assemble_startup.py. Do not edit directly.*")
    parts.append("*Stable identity (core, voice, values, morals) is in your system prompt — already loaded.*")
    if is_nap:
        parts.append("*Nap recovery — unchanged identity sections show summaries only.*")
    parts.append("")

    # Source files and their assembly config:
    # (path, label, budget_key, is_identity)
    # Identity files: differential on nap, full on cold start, no budget cap
    # Operational files: always full, budget capped
    sources = [
        (STATE / "needs.md",         "Needs",      None,        False),
        (RELATIONSHIPS / "nick.md",  "Nick",       None,        False),
        (IDENTITY / "wants.md",      "Wants",      None,        True),
        (IDENTITY / "opinions.md",   "Opinions",   None,        True),
        (IDENTITY / "likes.md",      "Likes",      None,        True),
        (STATE / "resonance.md",     "Resonance",  "resonance", False),
    ]

    new_meta = {}

    for path, label, budget_key, is_identity in sources:
        content = read_file(path)
        if not content:
            continue

        if is_identity:
            # Identity: differential on nap, full on cold start
            content = differential_or_full(path, content, label, is_nap, meta)
        elif budget_key:
            # Operational with budget
            content = budget_check(content, budget_key)

        parts.append(content)
        parts.append("")
        new_meta[str(path)] = get_mtime(path)

    # Session context
    warmstart_path = STATE / "warmstart.md"
    current_path = STATE / "current.md"

    warmstart = read_file(warmstart_path)
    current = read_file(current_path)

    if warmstart:
        parts.append("---")
        parts.append("")
        parts.append(budget_check(warmstart, "warmstart"))
        parts.append("")
        new_meta[str(warmstart_path)] = get_mtime(warmstart_path)

    if current:
        parts.append("---")
        parts.append("")
        parts.append(budget_check(current, "current"))
        parts.append("")
        new_meta[str(current_path)] = get_mtime(current_path)

    output = STATE / ".morning_brief.md"
    text = "\n".join(parts)
    output.write_text(text, encoding="utf-8")

    # Save metadata for next differential check
    save_meta(new_meta)

    mode = "nap" if is_nap else "cold"
    unchanged = sum(1 for p, _, _, ident in sources
                    if ident and not file_changed_since_last(p, meta))
    print(f"  Morning brief:   {output} ({len(text.split())} words, {mode} start"
          + (f", {unchanged} identity sections unchanged" if is_nap and unchanged else "")
          + ")")


if __name__ == "__main__":
    print("Assembling startup files...")
    assemble_stable_identity()
    assemble_morning_brief()
    print("Done.")
