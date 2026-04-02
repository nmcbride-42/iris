#!/usr/bin/env python3
"""
Send a message to a minion (or to Iris) via the dashboard API.

Usage:
    python send_message.py <to> <message> [--from name] [--priority normal|high|urgent]

Examples:
    python send_message.py strut "Review the curiosity engine queue logic"
    python send_message.py strut "Check the scout selection for domain bias" --priority high
    python send_message.py iris "Found a structural issue in the deploy pipeline" --from strut
"""

import argparse
import json
import os
import urllib.request

DASHBOARD_URL = os.environ.get("IRIS_DASHBOARD", "http://localhost:8051")


def send(to_name, content, from_name="iris", priority="normal"):
    url = f"{DASHBOARD_URL}/api/messages"
    data = json.dumps({
        "from": from_name,
        "to": to_name,
        "content": content,
        "priority": priority
    }).encode()

    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        result = json.loads(resp.read().decode())
        print(f"Sent message #{result['id']} to {to_name}")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a message to a minion")
    parser.add_argument("to", help="Recipient name (e.g. strut, iris)")
    parser.add_argument("message", help="Message content")
    parser.add_argument("--from", dest="from_name", default="iris", help="Sender name")
    parser.add_argument("--priority", default="normal", choices=["normal", "high", "urgent"])
    args = parser.parse_args()

    send(args.to, args.message, args.from_name, args.priority)
