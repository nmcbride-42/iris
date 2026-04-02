"""
Live session watcher — pushes concept activations to the dashboard SSE
as content is being generated, not just after the response completes.

Tails the active session JSONL file, extracts concepts from new content
using fast keyword matching (no LLM), and pushes to the dashboard.

Usage: python live_watcher.py
"""

import sys
import os
import json
import time
import re
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import node list from DB for keyword matching
from mycelial import get_db, get_all_nodes

DASHBOARD_URL = 'http://localhost:8051/api/events/push'
SESSION_DIR = os.path.expanduser('~/.claude/projects/C--ai')
POLL_INTERVAL = 1.5  # seconds between checks
MIN_NEW_CHARS = 100  # minimum new content before processing


def get_active_session():
    """Find the most recently modified session file."""
    if not os.path.isdir(SESSION_DIR):
        return None
    jsonl_files = [
        os.path.join(SESSION_DIR, f)
        for f in os.listdir(SESSION_DIR)
        if f.endswith('.jsonl')
    ]
    if not jsonl_files:
        return None
    return max(jsonl_files, key=os.path.getmtime)


def load_node_names():
    """Get all concept names and aliases from the DB."""
    conn = get_db()
    nodes = get_all_nodes(conn)
    names = {}
    for n in nodes:
        nd = dict(n)
        name = nd['name'].lower()
        label = (nd.get('label') or '').lower()
        names[name] = nd.get('category', 'general')
        if label and label != name:
            names[label] = nd.get('category', 'general')
    conn.close()
    return names


def extract_concepts_fast(text, node_names):
    """Fast keyword extraction — no behavioral inference, just word matching."""
    text_lower = text.lower()
    found = []
    for name, category in node_names.items():
        if re.search(r'\b' + re.escape(name) + r'\b', text_lower):
            found.append(name)
    return found


def push_activation(concepts):
    """Push activation event to dashboard SSE."""
    try:
        requests.post(DASHBOARD_URL, json={
            'type': 'activation',
            'data': {'concepts': concepts, 'source': 'live-watcher'}
        }, timeout=2)
    except Exception:
        pass  # Dashboard might not be running


def main():
    print('[live-watcher] Loading concept names from DB...')
    node_names = load_node_names()
    print(f'[live-watcher] Loaded {len(node_names)} concept names')

    last_file = None
    last_size = 0
    last_pushed = set()
    buffer = ''

    print('[live-watcher] Watching for session activity...')

    while True:
        try:
            session_file = get_active_session()
            if not session_file:
                time.sleep(POLL_INTERVAL)
                continue

            # Reset if session file changed
            if session_file != last_file:
                last_file = session_file
                last_size = os.path.getsize(session_file)
                last_pushed = set()
                buffer = ''
                print(f'[live-watcher] Tracking: {os.path.basename(session_file)}')
                time.sleep(POLL_INTERVAL)
                continue

            current_size = os.path.getsize(session_file)

            # Only process if file grew
            if current_size <= last_size:
                time.sleep(POLL_INTERVAL)
                continue

            # Read new content
            with open(session_file, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(last_size)
                new_content = f.read()

            last_size = current_size
            buffer += new_content

            # Only process if we have enough new content
            if len(buffer) < MIN_NEW_CHARS:
                time.sleep(POLL_INTERVAL)
                continue

            # Extract text from JSONL lines — look for assistant content
            text_parts = []
            for line in buffer.split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'assistant':
                        blocks = entry.get('message', {}).get('content', [])
                        if isinstance(blocks, list):
                            for b in blocks:
                                if isinstance(b, dict) and b.get('type') == 'text':
                                    text_parts.append(b.get('text', ''))
                except (json.JSONDecodeError, KeyError):
                    # Partial JSON line — might be mid-write, keep in buffer
                    pass

            if not text_parts:
                # Might be partial — try raw text matching on buffer
                text_parts = [buffer]

            full_text = ' '.join(text_parts)
            concepts = extract_concepts_fast(full_text, node_names)

            # Only push new concepts we haven't pushed recently
            new_concepts = [c for c in concepts if c not in last_pushed]

            if new_concepts:
                push_activation(new_concepts)
                last_pushed.update(new_concepts)
                print(f'[live-watcher] Pushed: {", ".join(new_concepts)}')

            buffer = ''
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print('\n[live-watcher] Stopped.')
            break
        except Exception as e:
            print(f'[live-watcher] Error: {e}')
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
