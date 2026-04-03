"""
Iris Mycelial Consolidation

Runs during nap/sleep to process the mycelial network:
- Full decay pass on all connections
- Prune dead connections (below threshold)
- Promote strong scout connections
- Calculate and report tip growth areas
- Process session transcript for concept co-occurrences

Idempotency: records a marker before decay. If interrupted and re-run,
skips decay to prevent double-decay (multiplicative: 0.95 * 0.95 = 0.9025).

Usage:
  python consolidate.py nap [session_file]
  python consolidate.py sleep [session_file]
"""

import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from mycelial import (
    get_db, run_decay, promote_scouts, get_tip_growth_candidates,
    get_network_stats, process_co_occurrences,
)
from hook import extract_concepts, infer_behavioral_concepts, prime_identity_concepts

MARKER_FILE = Path(__file__).parent / '.consolidation-marker'


def _check_idempotency(trigger):
    """Check if a previous consolidation was interrupted.
    Returns True if safe to proceed, False if decay should be skipped."""
    if MARKER_FILE.exists():
        try:
            data = json.loads(MARKER_FILE.read_text())
            if data.get('phase') == 'decay_started' and data.get('trigger') == trigger:
                print(f"  WARNING: Previous {trigger} consolidation was interrupted after decay.")
                print(f"  Skipping decay to prevent double-decay. Other steps will run.")
                return False
        except (json.JSONDecodeError, KeyError):
            pass
    return True


def _mark_phase(phase, trigger):
    """Record consolidation phase for idempotency."""
    MARKER_FILE.write_text(json.dumps({
        'phase': phase,
        'trigger': trigger,
        'timestamp': datetime.now().isoformat()
    }))


def _clear_marker():
    """Clear the consolidation marker on successful completion."""
    try:
        MARKER_FILE.unlink()
    except FileNotFoundError:
        pass


def process_session_transcript(conn, transcript_path, session_name=None):
    """
    Process a session JSONL file to extract all concept co-occurrences.
    Uses all three extraction layers (keyword + behavioral + primed).
    """
    if not os.path.exists(transcript_path):
        print(f"  Transcript not found: {transcript_path}")
        return 0

    from mycelial import get_all_nodes
    known_nodes = get_all_nodes(conn)
    known_names = {n['name'] for n in known_nodes}

    activations = 0
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get('type') == 'assistant':
                    msg = entry.get('message', {})
                    content = msg.get('content', '')
                    if isinstance(content, list):
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text_parts.append(block.get('text', ''))
                        content = ' '.join(text_parts)
                    if isinstance(content, str) and len(content) > 50:
                        # Layer 1: Keywords
                        concepts = extract_concepts(content, known_nodes)
                        # Layer 2: Behavioral inference
                        behavioral = infer_behavioral_concepts(content) & known_names
                        behavioral -= concepts  # don't double-count
                        # Layer 3: Identity priming
                        all_so_far = concepts | behavioral
                        primed = prime_identity_concepts(all_so_far, content) & known_names
                        primed -= all_so_far

                        all_concepts = concepts | behavioral | primed
                        if len(all_concepts) >= 2:
                            process_co_occurrences(
                                conn, all_concepts,
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
    try:
        print(f"Mycelial consolidation ({trigger})")
        print("=" * 40)

        # Step 1: Process transcript if provided
        if transcript_path:
            print(f"\n1. Processing session transcript (3-layer extraction)...")
            activations = process_session_transcript(conn, transcript_path, session_name=trigger)
            print(f"   Processed {activations} assistant messages")
        else:
            print(f"\n1. No transcript provided, skipping")

        # Step 2: Run decay (with idempotency check)
        safe_to_decay = _check_idempotency(trigger)
        if safe_to_decay:
            print(f"\n2. Running decay pass...")
            _mark_phase('decay_started', trigger)
            decay_result = run_decay(conn, trigger)
            _mark_phase('decay_complete', trigger)
            print(f"   Decayed {decay_result['decayed']} connections")
            print(f"   Pruned {decay_result['pruned']} dead connections (below threshold)")
            print(f"   Avg strength: {decay_result['avg_before']} -> {decay_result['avg_after']}")
            print(f"   Remaining: {decay_result['remaining']} connections")
        else:
            print(f"\n2. Decay skipped (idempotency — already ran)")

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

        # Step 6: WAL checkpoint — keep WAL file from growing indefinitely
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")

        _clear_marker()
        print(f"\nConsolidation complete.")
    finally:
        conn.close()


if __name__ == '__main__':
    trigger = sys.argv[1] if len(sys.argv) > 1 else 'nap'
    transcript = sys.argv[2] if len(sys.argv) > 2 else None
    consolidate(trigger, transcript)
