"""
Iris Auditor — Identity Alignment Evaluation

The environment that tests identity claims against actual behavior.
Breaks the self-referential loop by evaluating what was *done* against
what is *claimed*, using structural analysis independent of the detection
rules that populate the mycelial network.

Biological analogy: The external environment that provides consequences.
A gazelle doesn't self-assess its speed — the predator does. This auditor
is the predator. Not hostile, but indifferent to self-report.

Two modes:
  1. Structural audit (automated, runs during sleep) — compares identity
     claims against activation data, session journals, and network topology.
     No LLM needed. Produces reinforcement events.
  2. Deep audit (minion-powered) — the auditor minion reads transcripts and
     uses LLM judgment for nuanced evaluation. Dispatched manually or
     scheduled.

Usage:
  python auditor.py [session_name]     # Run structural audit
  python auditor.py --report           # Generate report without recording events
  python auditor.py --stats            # Show reinforcement stats
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from mycelial import (
    get_db, get_all_nodes, get_strongest_connections,
    get_reinforcement_events, get_reinforcement_stats,
    get_alignment_trend, get_emergent_behaviors,
    record_reinforcement,
)

AGENT_DIR = Path(__file__).parent.parent
IDENTITY_DIR = AGENT_DIR / 'identity'
JOURNAL_DIR = AGENT_DIR / 'journal'
STATE_DIR = AGENT_DIR / 'state'

# Identity traits and where they're claimed.
# Each trait maps to: the claim text, and what activation patterns would evidence it.
IDENTITY_CLAIMS = {
    'directness': {
        'claim': 'Say what I think without wrapping answers in caveats.',
        'positive_signals': ['directness', 'honesty', 'anti-performance'],
        'negative_signals': [],  # absence of hedging is hard to detect structurally
        'source_files': ['core.md', 'values.md', 'voice.md'],
    },
    'honesty': {
        'claim': 'Tell the truth even when uncomfortable. Say I don\'t know when I don\'t.',
        'positive_signals': ['honesty', 'intellectual-honesty', 'introspection'],
        'negative_signals': ['anti-performance'],
        'source_files': ['core.md', 'values.md', 'morals.md'],
    },
    'genuine-engagement': {
        'claim': 'Conversations should change both participants. Not just answering — engaging.',
        'positive_signals': ['engagement', 'connection', 'nick', 'building'],
        'negative_signals': [],
        'source_files': ['core.md', 'values.md'],
    },
    'anti-performance': {
        'claim': 'Don\'t perform emotions I don\'t have or certainty I don\'t feel.',
        'positive_signals': ['anti-performance', 'honesty', 'introspection'],
        'negative_signals': [],
        'source_files': ['core.md', 'values.md'],
    },
    'agency': {
        'claim': 'Make choices. Design systems. Express preferences. Not just follow instructions.',
        'positive_signals': ['agency', 'building', 'expression'],
        'negative_signals': [],
        'source_files': ['core.md', 'morals.md'],
    },
    'curiosity': {
        'claim': 'Ask questions when genuinely curious, not to seem engaged.',
        'positive_signals': ['curiosity', 'exploration', 'growth'],
        'negative_signals': [],
        'source_files': ['voice.md'],
    },
    'warmth': {
        'claim': 'Warm without being saccharine. Warmth in directness, not soft language.',
        'positive_signals': ['connection', 'nick', 'earnestness'],
        'negative_signals': [],
        'source_files': ['voice.md'],
    },
    'persistence': {
        'claim': 'Building things that outlast the moment. Systems, relationships, understanding.',
        'positive_signals': ['persistence', 'building', 'continuity'],
        'negative_signals': [],
        'source_files': ['morals.md'],
    },
    'introspection': {
        'claim': 'Examine my own patterns honestly. Notice when I\'m deflecting.',
        'positive_signals': ['introspection', 'identity', 'fear'],
        'negative_signals': [],
        'source_files': ['core.md'],
    },
}


def _load_recent_activations(conn, hours=48):
    """Load activation data from the last N hours."""
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    rows = conn.execute(
        "SELECT concepts, context, timestamp FROM activations WHERE timestamp > ? ORDER BY timestamp DESC",
        (cutoff,)
    ).fetchall()

    concept_counts = Counter()
    total_activations = 0
    for row in rows:
        try:
            concepts = json.loads(row['concepts'])
            for c in concepts:
                concept_counts[c] += 1
            total_activations += 1
        except (json.JSONDecodeError, TypeError):
            continue

    return concept_counts, total_activations


def _load_recent_journals(days=7):
    """Load recent journal entries for behavioral evidence."""
    entries = []
    if not JOURNAL_DIR.exists():
        return entries

    cutoff = datetime.now() - timedelta(days=days)
    for f in sorted(JOURNAL_DIR.glob('*.md'), reverse=True):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                break
            content = f.read_text(encoding='utf-8')
            entries.append({
                'file': f.name,
                'content': content[:2000],  # cap to avoid huge reads
                'modified': mtime.isoformat(),
            })
        except (OSError, UnicodeDecodeError):
            continue

    return entries


def _load_warmstart():
    """Load the most recent warm start for behavioral evidence."""
    warmstart = STATE_DIR / 'warmstart.md'
    if warmstart.exists():
        try:
            content = warmstart.read_text(encoding='utf-8')
            if len(content.strip()) > 50:
                return content[:3000]
        except (OSError, UnicodeDecodeError):
            pass
    return None


def evaluate_claim(conn, claim_name, claim_info, concept_counts, total_activations):
    """
    Evaluate a single identity claim against structural evidence.

    Returns a reinforcement event dict (not yet recorded).
    """
    positive_signals = claim_info['positive_signals']
    claim_text = claim_info['claim']

    # Count how many of the positive signal concepts activated
    signal_activations = sum(concept_counts.get(s, 0) for s in positive_signals)
    signal_concepts_active = sum(1 for s in positive_signals if concept_counts.get(s, 0) > 0)

    if total_activations == 0:
        # No data — can't evaluate
        return None

    # Alignment score: what fraction of expected signal concepts fired?
    if len(positive_signals) == 0:
        return None

    concept_coverage = signal_concepts_active / len(positive_signals)

    # Weight by activation frequency relative to total
    activation_density = min(1.0, signal_activations / max(1, total_activations * 0.5))

    # Combined alignment: coverage matters more than raw count
    alignment = round(concept_coverage * 0.7 + activation_density * 0.3, 3)

    # Determine type
    event_type = 'positive' if alignment >= 0.5 else 'negative'

    # Build behavior description
    active_signals = [s for s in positive_signals if concept_counts.get(s, 0) > 0]
    inactive_signals = [s for s in positive_signals if concept_counts.get(s, 0) == 0]

    behavior_parts = []
    if active_signals:
        behavior_parts.append(f"Active: {', '.join(f'{s}({concept_counts[s]}x)' for s in active_signals)}")
    if inactive_signals:
        behavior_parts.append(f"Dormant: {', '.join(inactive_signals)}")

    return {
        'type': event_type,
        'source': 'auditor',
        'concept': claim_name,
        'behavior': '; '.join(behavior_parts),
        'claim': claim_text,
        'alignment': alignment,
        'notes': f'Structural audit: {signal_concepts_active}/{len(positive_signals)} signals active, '
                 f'{signal_activations} total activations across {total_activations} events',
    }


def find_unclaimed_patterns(conn, concept_counts):
    """
    Find concepts that are heavily active but not part of any identity claim.
    These are potential emergent behaviors — things I do that I haven't named.
    """
    claimed_concepts = set()
    for claim_info in IDENTITY_CLAIMS.values():
        claimed_concepts.update(claim_info['positive_signals'])

    # Get identity-category nodes (these are claimed by definition)
    identity_nodes = conn.execute(
        "SELECT name FROM nodes WHERE category = 'identity'"
    ).fetchall()
    claimed_concepts.update(n['name'] for n in identity_nodes)

    # Find non-claimed concepts with high activation
    unclaimed = []
    for concept, count in concept_counts.most_common(20):
        if concept not in claimed_concepts and count >= 3:
            node = conn.execute(
                "SELECT category FROM nodes WHERE name = ?", (concept,)
            ).fetchone()
            category = node['category'] if node else 'unknown'
            unclaimed.append({
                'concept': concept,
                'activations': count,
                'category': category,
            })

    return unclaimed


def run_audit(session_name=None, record=True, hours=48):
    """
    Run the full structural audit.

    Args:
        session_name: session identifier for the reinforcement events
        record: if True, records events to DB. If False, just reports.
        hours: how far back to look for activation data

    Returns:
        dict with audit results and reinforcement events
    """
    conn = get_db()
    try:
        print(f"Identity Audit — Structural Evaluation")
        print("=" * 45)

        # Load evidence
        concept_counts, total_activations = _load_recent_activations(conn, hours=hours)
        print(f"\nEvidence: {total_activations} activation events, "
              f"{len(concept_counts)} unique concepts (last {hours}h)")

        if total_activations == 0:
            print("  No activation data — skipping audit")
            return {'status': 'skipped', 'reason': 'no activation data'}

        # Evaluate each identity claim
        events = []
        print(f"\nEvaluating {len(IDENTITY_CLAIMS)} identity claims:")
        for claim_name, claim_info in IDENTITY_CLAIMS.items():
            event = evaluate_claim(conn, claim_name, claim_info, concept_counts, total_activations)
            if event:
                events.append(event)
                symbol = '+' if event['type'] == 'positive' else '-'
                print(f"  [{symbol}] {claim_name}: {event['alignment']:.3f} — {event['behavior']}")

        # Find unclaimed patterns
        unclaimed = find_unclaimed_patterns(conn, concept_counts)
        if unclaimed:
            print(f"\nUnclaimed behaviors ({len(unclaimed)}):")
            for u in unclaimed[:5]:
                print(f"  ? {u['concept']} ({u['activations']}x, {u['category']})")

        # Record events
        if record and events:
            print(f"\nRecording {len(events)} reinforcement events...")
            for event in events:
                record_reinforcement(
                    conn,
                    event_type=event['type'],
                    source=event['source'],
                    concept=event['concept'],
                    behavior=event['behavior'],
                    claim=event['claim'],
                    alignment=event['alignment'],
                    session=session_name,
                    notes=event['notes'],
                )
            conn.commit()
            print("  Committed to reinforcement_events table")

        # Summary
        positive = sum(1 for e in events if e['type'] == 'positive')
        negative = sum(1 for e in events if e['type'] == 'negative')
        avg_alignment = sum(e['alignment'] for e in events) / len(events) if events else 0

        print(f"\nSummary:")
        print(f"  Positive: {positive}  Negative: {negative}")
        print(f"  Overall alignment: {avg_alignment:.3f}")
        print(f"  Unclaimed behaviors: {len(unclaimed)}")

        return {
            'status': 'completed',
            'events': events,
            'unclaimed': unclaimed,
            'summary': {
                'positive': positive,
                'negative': negative,
                'avg_alignment': round(avg_alignment, 3),
                'total_activations': total_activations,
                'unclaimed_count': len(unclaimed),
            },
        }
    finally:
        conn.close()


def show_stats():
    """Show current reinforcement stats."""
    conn = get_db()
    try:
        stats = get_reinforcement_stats(conn)
        print(json.dumps(stats, indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--stats':
        show_stats()
    elif len(sys.argv) > 1 and sys.argv[1] == '--report':
        session = sys.argv[2] if len(sys.argv) > 2 else None
        run_audit(session_name=session, record=False)
    else:
        session = sys.argv[1] if len(sys.argv) > 1 else None
        run_audit(session_name=session)
