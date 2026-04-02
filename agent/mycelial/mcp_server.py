"""
MCP Server for Iris Mycelial Network.

Exposes cognitive network queries as MCP tools so Iris can inspect
her own mycelial substrate through proper tool calls instead of
inline Python scripts. Uses stdio transport.
"""

import json
import os
import sys

# Make mycelial.py importable from the same directory
sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from mycelial import (
    get_db,
    get_cognitive_state,
    get_network_stats,
    get_node,
    get_connections_for_node,
    get_all_nodes,
    get_strongest_connections,
    get_decaying_connections,
    get_recent_activations,
    get_anastomosis_events,
)

mcp = FastMCP("iris-mycelial")


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows):
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    return [dict(r) for r in rows]


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
def iris_cognitive_state() -> str:
    """Returns current cognitive state: strongest connections, growing tips, and network stats. This is the startup query — what's most alive in the network right now."""
    conn = get_db()
    try:
        state = get_cognitive_state(conn)
        return json.dumps(state, indent=2, default=str)
    finally:
        conn.close()


@mcp.tool()
def iris_network_stats() -> str:
    """Returns network overview: node count, connection count, average strength, categories, active scouts, and anastomosis event count."""
    conn = get_db()
    try:
        stats = get_network_stats(conn)
        return json.dumps(stats, indent=2, default=str)
    finally:
        conn.close()


@mcp.tool()
def iris_search_nodes(query: str) -> str:
    """Search nodes by name (substring match). Returns matching nodes with their activation counts and categories."""
    conn = get_db()
    try:
        all_nodes = get_all_nodes(conn)
        query_lower = query.lower().strip()
        matches = [
            dict(n) for n in all_nodes
            if query_lower in n['name'] or query_lower in (n['label'] or '').lower()
        ]
        return json.dumps(matches, indent=2, default=str)
    finally:
        conn.close()


@mcp.tool()
def iris_node_detail(name: str) -> str:
    """Get a specific node and all its connections. Returns the node info plus every connection it has, sorted by strength."""
    conn = get_db()
    try:
        node = get_node(conn, name)
        if node is None:
            return json.dumps({"error": f"No node found with name '{name}'"})

        node_dict = dict(node)
        connections = get_connections_for_node(conn, node['id'])
        node_dict['connections'] = _rows_to_list(connections)

        return json.dumps(node_dict, indent=2, default=str)
    finally:
        conn.close()


@mcp.tool()
def iris_strongest_connections(limit: int = 25) -> str:
    """Get the strongest connections in the network, ranked by strength. These are the most reinforced pathways."""
    conn = get_db()
    try:
        connections = get_strongest_connections(conn, limit=limit)
        result = [
            {
                'source': c['source_name'],
                'target': c['target_name'],
                'strength': round(c['strength'], 4),
                'type': c['type'],
                'activation_count': c['activation_count'],
                'last_activated': c['last_activated'],
            }
            for c in connections
        ]
        return json.dumps(result, indent=2, default=str)
    finally:
        conn.close()


@mcp.tool()
def iris_recent_activations(limit: int = 20) -> str:
    """Get recent activation events — which concepts co-occurred and when. Shows the live pulse of the network."""
    conn = get_db()
    try:
        activations = get_recent_activations(conn, limit=limit)
        result = [
            {
                'timestamp': a['timestamp'],
                'session': a['session'],
                'concepts': json.loads(a['concepts']) if a['concepts'] else [],
                'context': a['context'],
                'strength_delta': a['strength_delta'],
            }
            for a in activations
        ]
        return json.dumps(result, indent=2, default=str)
    finally:
        conn.close()


@mcp.tool()
def iris_decaying_connections() -> str:
    """Get connections that are losing strength — fading pathways between 0.05 and 0.3 strength. These are at risk of being pruned."""
    conn = get_db()
    try:
        connections = get_decaying_connections(conn)
        result = [
            {
                'source': c['source_name'],
                'target': c['target_name'],
                'strength': round(c['strength'], 4),
                'type': c['type'],
                'last_activated': c['last_activated'],
            }
            for c in connections
        ]
        return json.dumps(result, indent=2, default=str)
    finally:
        conn.close()


@mcp.tool()
def iris_anastomosis_events(limit: int = 20) -> str:
    """Get recent anastomosis events — moments when a concept bridged two previously separate clusters. These are structural insights."""
    conn = get_db()
    try:
        events = get_anastomosis_events(conn, limit=limit)
        result = [
            {
                'timestamp': e['timestamp'],
                'bridge_node': e['bridge_name'],
                'cluster_a': json.loads(e['cluster_a']) if e['cluster_a'] else [],
                'cluster_b': json.loads(e['cluster_b']) if e['cluster_b'] else [],
                'description': e['description'],
            }
            for e in events
        ]
        return json.dumps(result, indent=2, default=str)
    finally:
        conn.close()


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
