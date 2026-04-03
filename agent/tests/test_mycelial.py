"""
Tests for the mycelial network core library (mycelial.py).

Covers node operations, connection management, co-occurrence processing,
decay, and network queries.
"""

import sys
import os
import sqlite3
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mycelial'))
from mycelial import (
    get_db, init_db, get_or_create_node, get_node, get_all_nodes,
    activate_node, get_or_create_connection, reinforce_connection,
    process_co_occurrences, run_decay, get_network_stats,
    get_strongest_connections, get_connections_for_node,
    _get_cluster, detect_anastomosis, create_scout,
    REINFORCE_AMOUNT, CO_OCCURRENCE_REINFORCE, DECAY_RATE_DEFAULT,
    ANASTOMOSIS_MIN_CLUSTER_SIZE,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a fresh test database for each test."""
    db_path = tmp_path / "test.db"
    # Copy schema to initialize
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'mycelial', 'schema.sql')
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    conn.close()
    return str(db_path)


class TestNodeOperations:

    def test_create_node(self, test_db):
        conn = get_db(test_db)
        node_id = get_or_create_node(conn, "honesty", category="identity")
        assert node_id > 0
        node = get_node(conn, "honesty")
        assert node is not None
        assert node["name"] == "honesty"
        assert node["category"] == "identity"
        conn.close()

    def test_get_existing_node(self, test_db):
        conn = get_db(test_db)
        id1 = get_or_create_node(conn, "honesty")
        id2 = get_or_create_node(conn, "honesty")
        assert id1 == id2
        conn.close()

    def test_name_normalization(self, test_db):
        conn = get_db(test_db)
        id1 = get_or_create_node(conn, "Warm Start")
        id2 = get_or_create_node(conn, "warm-start")
        assert id1 == id2
        conn.close()

    def test_activate_node(self, test_db):
        conn = get_db(test_db)
        node_id = get_or_create_node(conn, "curiosity")
        activate_node(conn, node_id)
        activate_node(conn, node_id)
        conn.commit()
        node = get_node(conn, "curiosity")
        assert node["activation_count"] == 2
        conn.close()

    def test_get_all_nodes(self, test_db):
        conn = get_db(test_db)
        get_or_create_node(conn, "a")
        get_or_create_node(conn, "b")
        get_or_create_node(conn, "c")
        nodes = get_all_nodes(conn)
        assert len(nodes) == 3
        conn.close()


class TestConnectionOperations:

    def test_create_connection(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "honesty")
        b = get_or_create_node(conn, "directness")
        c = get_or_create_connection(conn, a, b, conn_type="reinforcing")
        assert c["id"] > 0
        assert c["strength"] > 0
        conn.close()

    def test_connection_is_bidirectional(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "honesty")
        b = get_or_create_node(conn, "directness")
        c1 = get_or_create_connection(conn, a, b)
        c2 = get_or_create_connection(conn, b, a)
        assert c1["id"] == c2["id"]  # same connection regardless of direction
        conn.close()

    def test_reinforce_increases_strength(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "honesty")
        b = get_or_create_node(conn, "directness")
        c = get_or_create_connection(conn, a, b)
        old_strength = c["strength"]
        reinforce_connection(conn, c["id"])
        c2 = conn.execute("SELECT strength FROM connections WHERE id = ?", (c["id"],)).fetchone()
        assert c2["strength"] > old_strength
        conn.close()


class TestCoOccurrenceProcessing:

    def test_creates_connections_between_pairs(self, test_db):
        conn = get_db(test_db)
        # Create nodes first
        for name in ["honesty", "curiosity", "directness"]:
            get_or_create_node(conn, name, category="identity")

        connections, bridges = process_co_occurrences(
            conn, {"honesty", "curiosity", "directness"}, session="test"
        )
        # 3 concepts = 3 pairs
        assert len(connections) == 3
        conn.close()

    def test_reinforces_existing_connections(self, test_db):
        conn = get_db(test_db)
        for name in ["honesty", "curiosity"]:
            get_or_create_node(conn, name, category="identity")

        # First pass
        process_co_occurrences(conn, {"honesty", "curiosity"}, session="test1")
        c1 = get_strongest_connections(conn, limit=1)[0]
        s1 = c1["strength"]

        # Second pass — should reinforce
        process_co_occurrences(conn, {"honesty", "curiosity"}, session="test2")
        c2 = get_strongest_connections(conn, limit=1)[0]
        assert c2["strength"] > s1
        conn.close()

    def test_records_activation(self, test_db):
        conn = get_db(test_db)
        for name in ["honesty", "curiosity"]:
            get_or_create_node(conn, name, category="identity")

        process_co_occurrences(conn, {"honesty", "curiosity"}, session="test")
        activations = conn.execute("SELECT * FROM activations").fetchall()
        assert len(activations) == 1
        conn.close()


class TestDecay:

    def test_decay_reduces_strength(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "honesty")
        b = get_or_create_node(conn, "directness")
        c = get_or_create_connection(conn, a, b)
        old_strength = c["strength"]

        result = run_decay(conn, "test")
        c2 = conn.execute("SELECT strength FROM connections WHERE id = ?", (c["id"],)).fetchone()
        assert c2["strength"] < old_strength
        assert result["decayed"] >= 1
        conn.close()

    def test_decay_returns_stats(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "honesty")
        b = get_or_create_node(conn, "directness")
        get_or_create_connection(conn, a, b)

        result = run_decay(conn, "test")
        assert "decayed" in result
        assert "pruned" in result
        assert "avg_before" in result
        assert "avg_after" in result
        assert "remaining" in result
        conn.close()


class TestNetworkStats:

    def test_stats_on_empty_db(self, test_db):
        conn = get_db(test_db)
        stats = get_network_stats(conn)
        assert stats["total_nodes"] == 0
        assert stats["total_connections"] == 0
        conn.close()

    def test_stats_after_data(self, test_db):
        conn = get_db(test_db)
        for name in ["a", "b", "c"]:
            get_or_create_node(conn, name)
        process_co_occurrences(conn, {"a", "b", "c"}, session="test")

        stats = get_network_stats(conn)
        assert stats["total_nodes"] == 3
        assert stats["total_connections"] == 3
        assert stats["avg_strength"] > 0
        conn.close()


class TestClusterDetection:
    """Test _get_cluster BFS and anastomosis detection."""

    def test_single_node_cluster(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "isolated")
        conn.commit()
        cluster = _get_cluster(conn, a, min_strength=0.1)
        assert cluster == {a}
        conn.close()

    def test_connected_cluster(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "a")
        b = get_or_create_node(conn, "b")
        c = get_or_create_node(conn, "c")
        # Create strong connections a-b-c
        get_or_create_connection(conn, a, b)
        get_or_create_connection(conn, b, c)
        # Strengthen above min_strength
        conn.execute("UPDATE connections SET strength = 0.5")
        conn.commit()

        cluster = _get_cluster(conn, a, min_strength=0.2)
        assert a in cluster
        assert b in cluster
        assert c in cluster
        conn.close()

    def test_cluster_respects_min_strength(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "a")
        b = get_or_create_node(conn, "b")
        c = get_or_create_node(conn, "c")
        get_or_create_connection(conn, a, b)
        get_or_create_connection(conn, b, c)
        # a-b strong, b-c weak
        conn.execute("UPDATE connections SET strength = 0.5 WHERE source_id = ? AND target_id = ?",
                     (min(a, b), max(a, b)))
        conn.execute("UPDATE connections SET strength = 0.05 WHERE source_id = ? AND target_id = ?",
                     (min(b, c), max(b, c)))
        conn.commit()

        cluster = _get_cluster(conn, a, min_strength=0.2)
        assert a in cluster
        assert b in cluster
        assert c not in cluster  # too weak to be in cluster
        conn.close()

    def test_cluster_handles_cycles(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "a")
        b = get_or_create_node(conn, "b")
        c = get_or_create_node(conn, "c")
        get_or_create_connection(conn, a, b)
        get_or_create_connection(conn, b, c)
        get_or_create_connection(conn, a, c)  # cycle
        conn.execute("UPDATE connections SET strength = 0.5")
        conn.commit()

        cluster = _get_cluster(conn, a, min_strength=0.2)
        assert len(cluster) == 3  # all three in cycle
        conn.close()

    def test_anastomosis_detects_bridge(self, test_db):
        conn = get_db(test_db)
        # Create two separate clusters with internal connections above cluster walk
        # threshold (0.2) but bridge connections BELOW it (0.15) so the cluster
        # walk doesn't merge them through the bridge.
        a1 = get_or_create_node(conn, "cluster-a1")
        a2 = get_or_create_node(conn, "cluster-a2")
        a3 = get_or_create_node(conn, "cluster-a3")
        b1 = get_or_create_node(conn, "cluster-b1")
        b2 = get_or_create_node(conn, "cluster-b2")
        b3 = get_or_create_node(conn, "cluster-b3")
        bridge = get_or_create_node(conn, "bridge-node")

        # Cluster A: strongly connected internally
        for x, y in [(a1, a2), (a2, a3), (a1, a3)]:
            c = get_or_create_connection(conn, x, y)
            conn.execute("UPDATE connections SET strength = 0.6 WHERE id = ?", (c['id'],))

        # Cluster B: strongly connected internally
        for x, y in [(b1, b2), (b2, b3), (b1, b3)]:
            c = get_or_create_connection(conn, x, y)
            conn.execute("UPDATE connections SET strength = 0.6 WHERE id = ?", (c['id'],))

        # Bridge connects to both clusters at strength BELOW cluster walk threshold
        # (connections exist but cluster walk won't traverse them)
        c_ba = get_or_create_connection(conn, bridge, a1)
        c_bb = get_or_create_connection(conn, bridge, b1)
        conn.execute("UPDATE connections SET strength = 0.15 WHERE id IN (?, ?)",
                     (c_ba['id'], c_bb['id']))
        conn.commit()

        events = detect_anastomosis(conn, [bridge])
        # Bridge has connections to both clusters but clusters don't merge through it
        assert len(events) >= 1
        conn.close()

    def test_no_anastomosis_within_same_cluster(self, test_db):
        conn = get_db(test_db)
        a = get_or_create_node(conn, "a")
        b = get_or_create_node(conn, "b")
        c = get_or_create_node(conn, "c")
        for x, y in [(a, b), (b, c), (a, c)]:
            c_obj = get_or_create_connection(conn, x, y)
            conn.execute("UPDATE connections SET strength = 0.6 WHERE id = ?", (c_obj['id'],))
        conn.commit()

        events = detect_anastomosis(conn, [a])
        assert len(events) == 0  # all in same cluster, no bridge
        conn.close()


class TestTransactionSafety:
    """Test that operations properly commit/rollback."""

    def test_process_co_occurrences_is_atomic(self, test_db):
        conn = get_db(test_db)
        for name in ["x", "y"]:
            get_or_create_node(conn, name)
        conn.commit()

        process_co_occurrences(conn, {"x", "y"}, session="test")

        # Both activation record and connections should exist
        acts = conn.execute("SELECT COUNT(*) as c FROM activations").fetchone()['c']
        conns = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()['c']
        assert acts == 1
        assert conns == 1
        conn.close()

    def test_co_occurrence_rollback_on_error(self, test_db):
        """Verify process_co_occurrences rolls back on failure."""
        conn = get_db(test_db)
        get_or_create_node(conn, "r1")
        get_or_create_node(conn, "r2")
        conn.commit()

        before_conns = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()['c']
        before_acts = conn.execute("SELECT COUNT(*) as c FROM activations").fetchone()['c']

        # Trigger an error by breaking the activations table temporarily
        conn.execute("ALTER TABLE activations RENAME TO activations_broken")
        conn.commit()

        with pytest.raises(Exception):
            process_co_occurrences(conn, {"r1", "r2"}, session="fail-test")

        # Restore table
        conn.execute("ALTER TABLE activations_broken RENAME TO activations")
        conn.commit()

        # Connections should NOT have been created (rollback)
        after_conns = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()['c']
        after_acts = conn.execute("SELECT COUNT(*) as c FROM activations").fetchone()['c']
        assert after_conns == before_conns
        assert after_acts == before_acts
        conn.close()
