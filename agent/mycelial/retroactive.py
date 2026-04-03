"""
Retroactive Activation — Dream-phase concept injection

Called by the dream process to inject concepts that were enacted in a session
but not captured by the real-time hook. The dream process identifies these
through transcript review, then calls this script to update the DB.

Usage: python retroactive.py <concept1> <concept2> ... [--session SESSION] [--context CONTEXT]

The reinforcement is weaker than live co-occurrence (0.5x) because these are
inferred after the fact, not observed in real-time.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))
from mycelial import (
    get_db, get_node, get_or_create_node, activate_node,
    get_or_create_connection, reinforce_connection, CO_OCCURRENCE_REINFORCE
)

RETROACTIVE_WEIGHT = 0.5  # weaker than live, stronger than nothing


def inject_retroactive(concepts, session='dream-retroactive', context='Dream-phase retroactive activation'):
    """
    Inject a set of concepts as co-occurring, with reduced reinforcement.
    These were enacted but not captured by the real-time hook.
    """
    conn = get_db()
    try:
        # Resolve concepts to node IDs, skip unknown ones
        node_ids = {}
        skipped = []
        for name in concepts:
            canonical = name.lower().strip().replace(' ', '-')
            node = get_node(conn, canonical)
            if node:
                node_ids[canonical] = node['id']
                activate_node(conn, node['id'])
            else:
                skipped.append(canonical)

        if len(node_ids) < 2:
            return {
                'status': 'skipped',
                'reason': f'only {len(node_ids)} valid concepts',
                'skipped': skipped
            }

        # Create/reinforce connections between all pairs at reduced weight
        delta = CO_OCCURRENCE_REINFORCE * RETROACTIVE_WEIGHT
        names = list(node_ids.keys())
        updated = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                connection = get_or_create_connection(
                    conn, node_ids[names[i]], node_ids[names[j]],
                    origin=f"retroactive-{session}"
                )
                reinforce_connection(conn, connection['id'], delta)
                updated.append({'source': names[i], 'target': names[j]})

        # Log the activation
        conn.execute(
            "INSERT INTO activations (session, concepts, context, strength_delta) VALUES (?, ?, ?, ?)",
            (f"retroactive-{session}", json.dumps(names), context, delta)
        )
        conn.commit()

        return {
            'status': 'injected',
            'concepts': names,
            'connections_updated': len(updated),
            'strength_delta': delta,
            'skipped': skipped
        }
    finally:
        conn.close()


if __name__ == '__main__':
    concepts = []
    session = 'dream-retroactive'
    context = 'Dream-phase retroactive activation'

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--session' and i + 1 < len(args):
            session = args[i + 1]
            i += 2
        elif args[i] == '--context' and i + 1 < len(args):
            context = args[i + 1]
            i += 2
        else:
            concepts.append(args[i])
            i += 1

    if not concepts:
        print("Usage: python retroactive.py concept1 concept2 ... [--session S] [--context C]")
        sys.exit(1)

    result = inject_retroactive(concepts, session, context)
    print(json.dumps(result, indent=2))
