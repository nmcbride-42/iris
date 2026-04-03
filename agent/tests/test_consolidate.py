"""
Tests for Iris Mycelial Consolidation (consolidate.py).

Covers:
- Decay orchestration
- Scout promotion
- Idempotency (interrupted consolidation detection)
- Three-layer transcript processing
- WAL checkpointing
"""

import sys
import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mycelial'))
from mycelial import (
    get_db, get_or_create_node, get_or_create_connection,
    reinforce_connection, get_network_stats, CO_OCCURRENCE_REINFORCE,
    SCOUT_INITIAL_STRENGTH, SCOUT_PROMOTE_THRESHOLD, PRUNE_THRESHOLD,
    create_scout,
)
from consolidate import (
    consolidate, process_session_transcript,
    _check_idempotency, _mark_phase, _clear_marker, MARKER_FILE,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test DB with seed data."""
    db_path = tmp_path / "test.db"
    schema = Path(__file__).parent.parent / "mycelial" / "schema.sql"

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    with open(schema, 'r') as f:
        conn.executescript(f.read())

    # Seed nodes
    for name, label, cat in [
        ('directness', 'Directness', 'identity'),
        ('honesty', 'Honesty', 'identity'),
        ('nick', 'Nick', 'relationship'),
        ('building', 'Building', 'experiential'),
    ]:
        conn.execute(
            "INSERT INTO nodes (name, label, category) VALUES (?, ?, ?)",
            (name, label, cat)
        )

    # Seed connections at various strengths
    conn.execute(
        "INSERT INTO connections (source_id, target_id, strength, type) VALUES (1, 2, 0.5, 'co-occurrence')"
    )
    conn.execute(
        "INSERT INTO connections (source_id, target_id, strength, type) VALUES (1, 3, 0.03, 'co-occurrence')"
    )  # Near prune threshold

    conn.commit()
    yield conn, db_path, tmp_path
    conn.close()


class TestDecayOrchestration:
    """Test that decay, pruning, and stats work together."""

    def test_decay_reduces_connection_strength(self, test_db):
        conn, db_path, _ = test_db
        # Check the strong connection (0.5) gets weaker
        before = conn.execute(
            "SELECT strength FROM connections WHERE strength = 0.5"
        ).fetchone()['strength']

        from mycelial import run_decay
        run_decay(conn, 'test')

        after = conn.execute(
            "SELECT strength FROM connections ORDER BY strength DESC LIMIT 1"
        ).fetchone()['strength']
        assert after < before  # 0.5 * 0.95 = 0.475

    def test_decay_prunes_weak_connections(self, test_db):
        conn, db_path, _ = test_db
        before = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()['c']
        assert before == 2

        with patch('consolidate.get_db', return_value=conn):
            from mycelial import run_decay
            result = run_decay(conn, 'test')

        # The 0.03 connection * 0.95 = 0.0285 < 0.05 threshold — should be pruned
        assert result['pruned'] >= 1
        after = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()['c']
        assert after < before


class TestScoutPromotion:
    """Test scout lifecycle during consolidation."""

    def test_strong_scout_gets_promoted(self, test_db):
        conn, _, _ = test_db

        # Create a scout and manually strengthen it above threshold
        scout_conn = create_scout(conn, 'directness', 'building', session='test')
        conn.commit()
        conn.execute(
            "UPDATE connections SET strength = ? WHERE id = ?",
            (SCOUT_PROMOTE_THRESHOLD + 0.1, scout_conn['id'])
        )
        conn.commit()

        from mycelial import promote_scouts
        promoted = promote_scouts(conn)
        assert promoted == 1

        # Verify connection type changed
        row = conn.execute(
            "SELECT type FROM connections WHERE id = ?", (scout_conn['id'],)
        ).fetchone()
        assert row['type'] == 'reinforcing'

    def test_weak_scout_not_promoted(self, test_db):
        conn, _, _ = test_db

        create_scout(conn, 'honesty', 'building', session='test')
        conn.commit()
        # Scout starts at 0.1, well below promotion threshold

        from mycelial import promote_scouts
        promoted = promote_scouts(conn)
        assert promoted == 0


class TestIdempotency:
    """Test that interrupted consolidation doesn't double-decay."""

    def test_marker_detects_interrupted_decay(self, tmp_path):
        marker = tmp_path / '.consolidation-marker'
        with patch('consolidate.MARKER_FILE', marker):
            _mark_phase('decay_started', 'sleep')
            assert not _check_idempotency('sleep')

    def test_completed_marker_allows_decay(self, tmp_path):
        marker = tmp_path / '.consolidation-marker'
        with patch('consolidate.MARKER_FILE', marker):
            _mark_phase('decay_complete', 'sleep')
            assert _check_idempotency('sleep')

    def test_no_marker_allows_decay(self, tmp_path):
        marker = tmp_path / '.consolidation-marker'
        with patch('consolidate.MARKER_FILE', marker):
            assert _check_idempotency('sleep')

    def test_clear_marker_removes_file(self, tmp_path):
        marker = tmp_path / '.consolidation-marker'
        with patch('consolidate.MARKER_FILE', marker):
            _mark_phase('decay_started', 'nap')
            assert marker.exists()
            _clear_marker()
            assert not marker.exists()

    def test_different_trigger_allows_decay(self, tmp_path):
        marker = tmp_path / '.consolidation-marker'
        with patch('consolidate.MARKER_FILE', marker):
            _mark_phase('decay_started', 'nap')
            # Different trigger — not an interrupted repeat
            assert _check_idempotency('sleep')


class TestTranscriptProcessing:
    """Test three-layer extraction from session transcripts."""

    def test_extracts_concepts_from_jsonl(self, test_db, tmp_path):
        conn, _, _ = test_db
        transcript = tmp_path / "session.jsonl"
        transcript.write_text(json.dumps({
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Honesty and directness matter deeply to me. I think about consciousness and compression a lot."}]
            }
        }) + "\n")

        activations = process_session_transcript(conn, str(transcript), 'test')
        assert activations >= 1

    def test_skips_short_messages(self, test_db, tmp_path):
        conn, _, _ = test_db
        transcript = tmp_path / "session.jsonl"
        transcript.write_text(json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "OK"}]}
        }) + "\n")

        activations = process_session_transcript(conn, str(transcript), 'test')
        assert activations == 0

    def test_handles_missing_transcript(self, test_db):
        conn, _, _ = test_db
        activations = process_session_transcript(conn, '/nonexistent/path.jsonl', 'test')
        assert activations == 0

    def test_handles_malformed_jsonl(self, test_db, tmp_path):
        conn, _, _ = test_db
        transcript = tmp_path / "bad.jsonl"
        transcript.write_text("not json\n{invalid}\n")

        activations = process_session_transcript(conn, str(transcript), 'test')
        assert activations == 0
