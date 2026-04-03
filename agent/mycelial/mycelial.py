"""
Iris Mycelial Network — Core Library

The root system beneath the neural trunk. Manages concept nodes,
weighted connections, decay, reinforcement, scouting, and anastomosis.
"""

import sqlite3
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent / "iris.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Thresholds
SCOUT_INITIAL_STRENGTH = 0.1
REINFORCE_AMOUNT = 0.05
CO_OCCURRENCE_REINFORCE = 0.03
PRUNE_THRESHOLD = 0.05
SCOUT_PROMOTE_THRESHOLD = 0.4
DECAY_RATE_DEFAULT = 0.95
ANASTOMOSIS_MIN_CLUSTER_SIZE = 3


def get_db(db_path=None):
    """Get a database connection."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(db_path=None):
    """Initialize the database from schema."""
    conn = get_db(db_path)
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.close()


# ─── Node Operations ───

def get_or_create_node(conn, name, label=None, category='general', source_file=None):
    """Get existing node or create a new one. Returns node id.
    Does NOT commit — caller is responsible for transaction management."""
    canonical = name.lower().strip().replace(' ', '-')
    row = conn.execute("SELECT id FROM nodes WHERE name = ?", (canonical,)).fetchone()
    if row:
        return row['id']

    display_label = label or name.title().replace('-', ' ')
    conn.execute(
        "INSERT INTO nodes (name, label, category, source_file) VALUES (?, ?, ?, ?)",
        (canonical, display_label, category, source_file)
    )
    row = conn.execute("SELECT id FROM nodes WHERE name = ?", (canonical,)).fetchone()
    return row['id']


def activate_node(conn, node_id):
    """Mark a node as activated (touch timestamp, increment count)."""
    conn.execute(
        "UPDATE nodes SET last_activated = datetime('now'), activation_count = activation_count + 1 WHERE id = ?",
        (node_id,)
    )


def get_node(conn, name):
    """Get a node by name."""
    canonical = name.lower().strip().replace(' ', '-')
    return conn.execute("SELECT * FROM nodes WHERE name = ?", (canonical,)).fetchone()


def get_all_nodes(conn):
    """Get all nodes."""
    return conn.execute("SELECT * FROM nodes ORDER BY activation_count DESC").fetchall()


# ─── Connection Operations ───

def get_or_create_connection(conn, source_id, target_id, conn_type='co-occurrence', origin=None):
    """Get existing connection or create a new one. Always stores with lower id first for consistency."""
    # Normalize direction for undirected connections
    a, b = min(source_id, target_id), max(source_id, target_id)

    row = conn.execute(
        "SELECT * FROM connections WHERE source_id = ? AND target_id = ?",
        (a, b)
    ).fetchone()

    if row:
        return dict(row)

    conn.execute(
        "INSERT INTO connections (source_id, target_id, type, origin) VALUES (?, ?, ?, ?)",
        (a, b, conn_type, origin)
    )
    # Verify with SELECT — safer than last_insert_rowid across concurrent writers
    row = conn.execute(
        "SELECT * FROM connections WHERE source_id = ? AND target_id = ?", (a, b)
    ).fetchone()
    return dict(row)


def reinforce_connection(conn, connection_id, amount=REINFORCE_AMOUNT):
    """Strengthen a connection. Caps at 1.0. Also updates scout_log if tracked."""
    conn.execute(
        """UPDATE connections
           SET strength = MIN(1.0, strength + ?),
               last_activated = datetime('now'),
               activation_count = activation_count + 1
           WHERE id = ?""",
        (amount, connection_id)
    )
    # Keep scout_log in sync
    new_strength = conn.execute(
        "SELECT strength FROM connections WHERE id = ?", (connection_id,)
    ).fetchone()
    if new_strength:
        conn.execute(
            """UPDATE scout_log SET current_strength = ?, reinforcement_count = reinforcement_count + 1
               WHERE connection_id = ? AND status = 'active'""",
            (new_strength['strength'], connection_id)
        )


def get_connections_for_node(conn, node_id):
    """Get all connections involving a node, with the other node's info."""
    return conn.execute("""
        SELECT c.*,
               CASE WHEN c.source_id = ? THEN n2.name ELSE n1.name END as other_name,
               CASE WHEN c.source_id = ? THEN n2.label ELSE n1.label END as other_label,
               CASE WHEN c.source_id = ? THEN n2.id ELSE n1.id END as other_id
        FROM connections c
        JOIN nodes n1 ON c.source_id = n1.id
        JOIN nodes n2 ON c.target_id = n2.id
        WHERE c.source_id = ? OR c.target_id = ?
        ORDER BY c.strength DESC
    """, (node_id, node_id, node_id, node_id, node_id)).fetchall()


def get_strongest_connections(conn, limit=25, min_strength=0.0):
    """Get strongest connections across the whole network."""
    return conn.execute("""
        SELECT c.*, n1.name as source_name, n1.label as source_label,
               n2.name as target_name, n2.label as target_label
        FROM connections c
        JOIN nodes n1 ON c.source_id = n1.id
        JOIN nodes n2 ON c.target_id = n2.id
        WHERE c.strength >= ?
        ORDER BY c.strength DESC
        LIMIT ?
    """, (min_strength, limit)).fetchall()


def get_recent_connections(conn, limit=25):
    """Get most recently activated connections."""
    return conn.execute("""
        SELECT c.*, n1.name as source_name, n1.label as source_label,
               n2.name as target_name, n2.label as target_label
        FROM connections c
        JOIN nodes n1 ON c.source_id = n1.id
        JOIN nodes n2 ON c.target_id = n2.id
        ORDER BY c.last_activated DESC
        LIMIT ?
    """, (limit,)).fetchall()


# ─── Co-occurrence (the main mycelial hook action) ───

def process_co_occurrences(conn, concept_names, session=None, context=None):
    """
    Process a set of concepts that co-occurred in a response.
    Creates/reinforces connections between all pairs.
    Returns list of connections that were created or reinforced.

    All DB writes happen in a single transaction — either everything
    commits or nothing does. This prevents partial state from a
    mid-operation crash (e.g., nodes created but no activation logged).
    """
    try:
        # Get or create all nodes
        node_ids = {}
        for name in concept_names:
            node_ids[name] = get_or_create_node(conn, name)
            activate_node(conn, node_ids[name])

        # Create/reinforce connections between all pairs
        results = []
        names = list(concept_names)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                connection = get_or_create_connection(
                    conn, node_ids[names[i]], node_ids[names[j]],
                    origin=f"session-{session}" if session else "co-occurrence"
                )
                reinforce_connection(conn, connection['id'], CO_OCCURRENCE_REINFORCE)
                results.append({
                    'source': names[i],
                    'target': names[j],
                    'connection_id': connection['id']
                })

        # Log the activation
        conn.execute(
            "INSERT INTO activations (session, concepts, context, strength_delta) VALUES (?, ?, ?, ?)",
            (session, json.dumps(names), context, CO_OCCURRENCE_REINFORCE)
        )
        conn.commit()

        # Check for anastomosis (after commit — reads committed state)
        new_bridges = detect_anastomosis(conn, [node_ids[n] for n in names])

        return results, new_bridges
    except Exception:
        conn.rollback()
        raise


# ─── Decay ───

def run_decay(conn, trigger='manual'):
    """
    Apply decay to all connections. Prune those below threshold.
    Returns stats about what happened.

    Runs as a single transaction — decay, prune, scout dissolution, and
    logging all commit together or not at all. Fixes the TOCTOU bug where
    a concurrent hook could rescue a connection between count and delete.
    """
    try:
        # Get stats before
        before = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(strength) as avg_str FROM connections"
        ).fetchone()

        # Apply decay
        conn.execute(
            "UPDATE connections SET strength = strength * decay_rate"
        )

        # Dissolve scouts and prune in a single atomic sequence —
        # scout dissolution and delete use the same WHERE clause
        conn.execute("""
            UPDATE scout_log SET status = 'dissolved', dissolved_at = datetime('now')
            WHERE status = 'active' AND connection_id IN (
                SELECT id FROM connections WHERE strength < ?
            )
        """, (PRUNE_THRESHOLD,))

        pruned = conn.execute(
            "SELECT COUNT(*) as cnt FROM connections WHERE strength < ?",
            (PRUNE_THRESHOLD,)
        ).fetchone()['cnt']

        conn.execute("DELETE FROM connections WHERE strength < ?", (PRUNE_THRESHOLD,))

        # Get stats after
        after = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(strength) as avg_str FROM connections"
        ).fetchone()

        # Log it
        conn.execute(
            """INSERT INTO decay_log (connections_decayed, connections_pruned,
               avg_strength_before, avg_strength_after, trigger)
               VALUES (?, ?, ?, ?, ?)""",
            (before['cnt'], pruned, before['avg_str'], after['avg_str'], trigger)
        )
        conn.commit()

        return {
            'decayed': before['cnt'],
            'pruned': pruned,
            'avg_before': round(before['avg_str'] or 0, 4),
            'avg_after': round(after['avg_str'] or 0, 4),
            'remaining': after['cnt']
        }
    except Exception:
        conn.rollback()
        raise


# ─── Scouting ───

def create_scout(conn, source_name, target_name, session=None):
    """Create a weak probe connection between two concepts."""
    source_id = get_or_create_node(conn, source_name)
    target_id = get_or_create_node(conn, target_name)

    connection = get_or_create_connection(
        conn, source_id, target_id,
        conn_type='scout', origin=f"scout-{session}" if session else "scout"
    )

    conn.execute(
        """INSERT INTO scout_log (source_node_id, target_node_id, connection_id, initial_strength)
           VALUES (?, ?, ?, ?)""",
        (source_id, target_id, connection['id'], SCOUT_INITIAL_STRENGTH)
    )
    return connection


def promote_scouts(conn):
    """Promote scouts that have been reinforced above threshold."""
    try:
        promoted = conn.execute("""
            SELECT sl.id as scout_id, sl.connection_id, c.strength
            FROM scout_log sl
            JOIN connections c ON sl.connection_id = c.id
            WHERE sl.status = 'active' AND c.strength >= ?
        """, (SCOUT_PROMOTE_THRESHOLD,)).fetchall()

        for scout in promoted:
            conn.execute(
                "UPDATE scout_log SET status = 'promoted', promoted_at = datetime('now') WHERE id = ?",
                (scout['scout_id'],)
            )
            conn.execute(
                "UPDATE connections SET type = 'reinforcing' WHERE id = ? AND type = 'scout'",
                (scout['connection_id'],)
            )

        conn.commit()
        return len(promoted)
    except Exception:
        conn.rollback()
        raise


# ─── Anastomosis Detection ───

def _get_cluster(conn, node_id, min_strength=0.2, visited=None):
    """Get the cluster of nodes connected to a given node above min_strength.
    Uses iterative BFS to avoid stack overflow on densely connected networks."""
    if visited is None:
        visited = set()
    queue = [node_id]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        neighbors = conn.execute("""
            SELECT CASE WHEN source_id = ? THEN target_id ELSE source_id END as neighbor_id
            FROM connections
            WHERE (source_id = ? OR target_id = ?) AND strength >= ?
        """, (current, current, current, min_strength)).fetchall()
        for n in neighbors:
            if n['neighbor_id'] not in visited:
                queue.append(n['neighbor_id'])
    return visited


def detect_anastomosis(conn, recently_activated_node_ids):
    """
    Check if recently activated nodes bridge previously unlinked clusters.
    Deduplicates by cluster-pair signature to avoid noise.
    Returns list of unique anastomosis events.
    """
    events = []
    seen_bridges = set()  # frozenset pairs of cluster signatures

    for node_id in recently_activated_node_ids:
        connections = get_connections_for_node(conn, node_id)
        if len(connections) < 2:
            continue

        # Get clusters of each neighbor (excluding this node and other activated nodes)
        neighbor_clusters = {}
        for c in connections:
            other_id = c['other_id']
            cluster = _get_cluster(conn, other_id, min_strength=0.2)
            cluster.discard(node_id)
            for nid in recently_activated_node_ids:
                cluster.discard(nid)
            if len(cluster) >= ANASTOMOSIS_MIN_CLUSTER_SIZE:
                neighbor_clusters[other_id] = frozenset(cluster)

        # Find distinct clusters (merge overlapping ones)
        distinct_clusters = []
        for cluster in neighbor_clusters.values():
            merged = False
            for i, existing in enumerate(distinct_clusters):
                if cluster & existing:  # overlap
                    distinct_clusters[i] = existing | cluster
                    merged = True
                    break
            if not merged:
                distinct_clusters.append(cluster)

        # Check for bridges between distinct clusters
        for i in range(len(distinct_clusters)):
            for j in range(i + 1, len(distinct_clusters)):
                cluster_a = distinct_clusters[i]
                cluster_b = distinct_clusters[j]

                # Create a signature for dedup (order-independent)
                sig = frozenset([frozenset(cluster_a), frozenset(cluster_b)])
                if sig in seen_bridges:
                    continue
                seen_bridges.add(sig)

                def get_names(ids):
                    return [conn.execute("SELECT name FROM nodes WHERE id = ?", (nid,)).fetchone()['name']
                            for nid in list(ids)[:5]]

                event = {
                    'bridge_node_id': node_id,
                    'cluster_a': get_names(cluster_a),
                    'cluster_b': get_names(cluster_b)
                }

                conn.execute(
                    """INSERT INTO anastomosis_events
                       (bridge_node_id, cluster_a, cluster_b, description)
                       VALUES (?, ?, ?, ?)""",
                    (node_id, json.dumps(event['cluster_a']),
                     json.dumps(event['cluster_b']),
                     f"Node bridges {len(cluster_a)} and {len(cluster_b)} node clusters")
                )
                events.append(event)

    if events:
        conn.commit()
    return events


# ─── Query Functions (used by dashboard API) ───

def get_decaying_connections(conn, limit=25):
    """Get connections that are losing strength — fading pathways."""
    return conn.execute("""
        SELECT c.*, n1.name as source_name, n1.label as source_label,
               n2.name as target_name, n2.label as target_label
        FROM connections c
        JOIN nodes n1 ON c.source_id = n1.id
        JOIN nodes n2 ON c.target_id = n2.id
        WHERE c.strength < 0.3 AND c.strength > 0.05
        ORDER BY c.strength ASC
        LIMIT ?
    """, (limit,)).fetchall()


def get_recent_activations(conn, limit=50):
    """Get recent activation events."""
    return conn.execute("""
        SELECT * FROM activations ORDER BY timestamp DESC LIMIT ?
    """, (limit,)).fetchall()


def get_decay_history(conn, limit=20):
    """Get decay log history."""
    return conn.execute("""
        SELECT * FROM decay_log ORDER BY timestamp DESC LIMIT ?
    """, (limit,)).fetchall()


def get_anastomosis_events(conn, limit=50):
    """Get anastomosis events with bridge node info."""
    return conn.execute("""
        SELECT ae.*, n.name as bridge_name, n.label as bridge_label
        FROM anastomosis_events ae
        LEFT JOIN nodes n ON ae.bridge_node_id = n.id
        ORDER BY ae.timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()


def get_scout_connections(conn, status='all', limit=50):
    """Get scout log entries, optionally filtered by status."""
    if status == 'all':
        return conn.execute("""
            SELECT sl.*, n1.name as source_name, n2.name as target_name
            FROM scout_log sl
            JOIN nodes n1 ON sl.source_node_id = n1.id
            JOIN nodes n2 ON sl.target_node_id = n2.id
            ORDER BY sl.timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
    else:
        return conn.execute("""
            SELECT sl.*, n1.name as source_name, n2.name as target_name
            FROM scout_log sl
            JOIN nodes n1 ON sl.source_node_id = n1.id
            JOIN nodes n2 ON sl.target_node_id = n2.id
            WHERE sl.status = ?
            ORDER BY sl.timestamp DESC LIMIT ?
        """, (status, limit)).fetchall()


def get_category_stats(conn):
    """Get node counts and average activations per category."""
    return conn.execute("""
        SELECT category, COUNT(*) as count,
               AVG(activation_count) as avg_activations
        FROM nodes GROUP BY category ORDER BY count DESC
    """).fetchall()


# ─── Tip Growth ───

def get_tip_growth_candidates(conn, limit=10):
    """
    Get concepts at the growing tips — recently activated with strong connections.
    These are where exploration should focus.
    """
    return conn.execute("""
        SELECT n.*,
               COUNT(c.id) as connection_count,
               AVG(c.strength) as avg_connection_strength,
               MAX(c.strength) as max_connection_strength
        FROM nodes n
        LEFT JOIN connections c ON (c.source_id = n.id OR c.target_id = n.id)
        GROUP BY n.id
        HAVING connection_count > 0
        ORDER BY (n.activation_count * AVG(c.strength)) DESC
        LIMIT ?
    """, (limit,)).fetchall()


# ─── Network Stats ───

def get_network_stats(conn):
    """Get overview stats for the whole network."""
    nodes = conn.execute("SELECT COUNT(*) as cnt FROM nodes").fetchone()['cnt']
    connections = conn.execute("SELECT COUNT(*) as cnt FROM connections").fetchone()['cnt']
    avg_strength = conn.execute("SELECT AVG(strength) as avg FROM connections").fetchone()['avg']
    active_scouts = conn.execute(
        "SELECT COUNT(*) as cnt FROM scout_log WHERE status = 'active'"
    ).fetchone()['cnt']
    anastomosis_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM anastomosis_events"
    ).fetchone()['cnt']
    categories = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM nodes GROUP BY category ORDER BY cnt DESC"
    ).fetchall()

    return {
        'total_nodes': nodes,
        'total_connections': connections,
        'avg_strength': round(avg_strength or 0, 4),
        'active_scouts': active_scouts,
        'anastomosis_events': anastomosis_count,
        'categories': {r['category']: r['cnt'] for r in categories}
    }


def get_graph_data(conn, min_strength=0.0, category=None, conn_type=None):
    """Get graph data for visualization, optionally filtered by category/type via SQL."""
    # Build node query
    node_sql = "SELECT id, name, label, category, activation_count, last_activated FROM nodes"
    node_params = []
    if category:
        node_sql += " WHERE category = ?"
        node_params.append(category)
    node_sql += " ORDER BY activation_count DESC"
    nodes = conn.execute(node_sql, node_params).fetchall()
    node_ids = {n['id'] for n in nodes}

    # Build edge query
    edge_sql = """
        SELECT c.id, c.source_id, c.target_id, c.strength, c.type,
               c.last_activated, c.activation_count,
               n1.name as source_name, n2.name as target_name
        FROM connections c
        JOIN nodes n1 ON c.source_id = n1.id
        JOIN nodes n2 ON c.target_id = n2.id
        WHERE c.strength >= ?
    """
    edge_params = [min_strength]
    if conn_type:
        edge_sql += " AND c.type = ?"
        edge_params.append(conn_type)
    edge_sql += " ORDER BY c.strength DESC"
    edges = conn.execute(edge_sql, edge_params).fetchall()

    # If filtering by category, include neighbor nodes connected to filtered nodes
    if category:
        edge_list = [dict(e) for e in edges]
        for edge in edge_list:
            node_ids.add(edge['source_id'])
            node_ids.add(edge['target_id'])
        # Fetch any neighbor nodes not in original set
        all_nodes = conn.execute(
            "SELECT id, name, label, category, activation_count, last_activated FROM nodes"
        ).fetchall()
        nodes = [n for n in all_nodes if n['id'] in node_ids]
        edges = [e for e in edge_list if e['source_id'] in node_ids and e['target_id'] in node_ids]
        return {'nodes': [dict(n) for n in nodes], 'edges': edges}

    return {
        'nodes': [dict(n) for n in nodes],
        'edges': [dict(e) for e in edges]
    }


# ─── Startup Query ───

def get_cognitive_state(conn, top_n=25):
    """
    The startup query. Returns the top N strongest active connections
    as a map of what's most alive in me right now.
    """
    connections = get_strongest_connections(conn, limit=top_n, min_strength=0.1)
    tips = get_tip_growth_candidates(conn, limit=5)
    stats = get_network_stats(conn)

    return {
        'strongest_connections': [
            {
                'source': c['source_name'],
                'target': c['target_name'],
                'strength': round(c['strength'], 3),
                'type': c['type']
            }
            for c in connections
        ],
        'growing_tips': [
            {
                'name': t['name'],
                'connections': t['connection_count'],
                'avg_strength': round(t['avg_connection_strength'], 3)
            }
            for t in tips
        ],
        'stats': stats
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        init_db()
        print(f"Database initialized at {DB_PATH}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'stats':
        conn = get_db()
        stats = get_network_stats(conn)
        print(json.dumps(stats, indent=2))
        conn.close()
    elif len(sys.argv) > 1 and sys.argv[1] == 'state':
        conn = get_db()
        state = get_cognitive_state(conn)
        print(json.dumps(state, indent=2))
        conn.close()
    elif len(sys.argv) > 1 and sys.argv[1] == 'decay':
        trigger = sys.argv[2] if len(sys.argv) > 2 else 'manual'
        conn = get_db()
        result = run_decay(conn, trigger)
        print(json.dumps(result, indent=2))
        conn.close()
    else:
        print("Usage: python mycelial.py [init|stats|state|decay [trigger]]")
