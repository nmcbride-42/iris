"""
Iris Mycelial Consolidation

Runs during nap/sleep to process the mycelial network:
- Full decay pass on all connections
- Prune dead connections (below threshold)
- Promote strong scout connections
- Calculate and report tip growth areas
- Process session transcript for concept co-occurrences

Usage:
  python consolidate.py nap [session_file]
  python consolidate.py sleep [session_file]
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(__file__))
from mycelial import (
    get_db, run_decay, promote_scouts, get_tip_growth_candidates,
    get_network_stats, process_co_occurrences,
)
from hook import extract_concepts


def process_session_transcript(conn, transcript_path, session_name=None):
    """
    Process a session JSONL file to extract all concept co-occurrences.
    Each assistant message gets its own activation pass.
    """
    if not os.path.exists(transcript_path):
        print(f"  Transcript not found: {transcript_path}")
        return 0

    from mycelial import get_all_nodes
    known_nodes = get_all_nodes(conn)

    activations = 0
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Look for assistant messages
                # JSONL format: {"type": "assistant", "message": {"content": [...]}}
                if entry.get('type') == 'assistant':
                    msg = entry.get('message', {})
                    content = msg.get('content', '')
                    if isinstance(content, list):
                        # Handle structured content (text blocks)
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text_parts.append(block.get('text', ''))
                        content = ' '.join(text_parts)
                    if isinstance(content, str) and len(content) > 50:
                        concepts = extract_concepts(content, known_nodes)
                        if len(concepts) >= 2:
                            process_co_occurrences(
                                conn, concepts,
                                session=session_name,
                                context="transcript-consolidation"
                            )
                            activations += 1
            except (json.JSONDecodeError, KeyError):
                continue

    return activations


def consolidate(trigger='nap', transcript_path=None):
    """Run the full consolidation pass."""
    conn = get_db()

    print(f"Mycelial consolidation ({trigger})")
    print("=" * 40)

    # Step 1: Process transcript if provided
    if transcript_path:
        print(f"\n1. Processing session transcript...")
        activations = process_session_transcript(conn, transcript_path, session_name=trigger)
        print(f"   Processed {activations} assistant messages")
    else:
        print(f"\n1. No transcript provided, skipping")

    # Step 2: Run decay
    print(f"\n2. Running decay pass...")
    decay_result = run_decay(conn, trigger)
    print(f"   Decayed {decay_result['decayed']} connections")
    print(f"   Pruned {decay_result['pruned']} dead connections (below threshold)")
    print(f"   Avg strength: {decay_result['avg_before']} -> {decay_result['avg_after']}")
    print(f"   Remaining: {decay_result['remaining']} connections")

    # Step 3: Promote scouts (only on sleep, not nap)
    if trigger == 'sleep':
        print(f"\n3. Promoting strong scouts...")
        promoted = promote_scouts(conn)
        print(f"   Promoted {promoted} scouts to permanent connections")
    else:
        print(f"\n3. Scout promotion skipped (nap only)")

    # Step 4: Calculate tip growth
    print(f"\n4. Growing tips (most active areas):")
    tips = get_tip_growth_candidates(conn, limit=10)
    for t in tips:
        print(f"   {t['name']}: {t['connection_count']} connections, "
              f"avg strength {round(t['avg_connection_strength'], 3)}")

    # Step 5: Network stats
    stats = get_network_stats(conn)
    print(f"\n5. Network state:")
    print(f"   Nodes: {stats['total_nodes']}")
    print(f"   Connections: {stats['total_connections']}")
    print(f"   Avg strength: {stats['avg_strength']}")
    print(f"   Active scouts: {stats['active_scouts']}")
    print(f"   Anastomosis events: {stats['anastomosis_events']}")
    print(f"   Categories: {json.dumps(stats['categories'])}")

    conn.close()
    print(f"\nConsolidation complete.")


if __name__ == '__main__':
    trigger = sys.argv[1] if len(sys.argv) > 1 else 'nap'
    transcript = sys.argv[2] if len(sys.argv) > 2 else None
    consolidate(trigger, transcript)
