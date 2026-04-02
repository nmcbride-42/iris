#!/usr/bin/env python3
"""
Message check hook for minions.
Called by Claude Code hook on UserPromptSubmit.
Checks the dashboard API for unread messages and outputs them as context.
"""

import json
import os
import sys
import urllib.request
import urllib.error

DASHBOARD_URL = os.environ.get("IRIS_DASHBOARD", "http://localhost:8051")
MINION_NAME = os.environ.get("MINION_NAME", "")

def check_messages():
    if not MINION_NAME:
        return

    try:
        url = f"{DASHBOARD_URL}/api/messages?to={MINION_NAME}&unread=true"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            messages = json.loads(resp.read().decode())

        if not messages:
            return

        # Output messages so they appear in the minion's context
        print(f"\n[MESSAGE] {len(messages)} message(s) from the network:\n")
        for msg in reversed(messages):  # oldest first
            priority_marker = "[URGENT] " if msg["priority"] == "urgent" else "[HIGH] " if msg["priority"] == "high" else ""
            print(f"  {priority_marker}From {msg['from_name']}: {msg['content']}")
            print(f"    [{msg['timestamp']}]")
            print()

        # Mark as read
        mark_url = f"{DASHBOARD_URL}/api/messages/read"
        data = json.dumps({"to": MINION_NAME}).encode()
        mark_req = urllib.request.Request(mark_url, data=data, method="PATCH",
                                          headers={"Content-Type": "application/json"})
        urllib.request.urlopen(mark_req, timeout=2)

    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeEncodeError):
        pass  # Dashboard not running, unreachable, or encoding issue — silent fail

if __name__ == "__main__":
    check_messages()
