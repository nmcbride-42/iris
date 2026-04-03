"""
Tests for retroactive activation (retroactive.py).

Covers:
- Weight calculations
- Unknown concept handling
- Edge cases (empty, single concept, duplicates)
- Connection cleanup
"""

import sys
import os
import json
import pytest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mycelial'))
from mycelial import get_db, CO_OCCURRENCE_REINFORCE
from retroactive import inject_retroactive, RETROACTIVE_WEIGHT


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
    conn.commit()
    yield conn, db_path
    conn.close()


class TestRetroactiveInjection:
    """Test retroactive concept injection."""

    def test_creates_connections_between_concepts(self, test_db, monkeypatch):
        conn, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: conn)

        result = inject_retroactive(['directness', 'honesty', 'nick'])
        assert result['status'] == 'injected'
        assert result['connections_updated'] == 3  # 3 pairs from 3 concepts
        assert len(result['skipped']) == 0

    def test_weight_is_reduced(self, test_db, monkeypatch):
        conn, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: conn)

        expected_delta = CO_OCCURRENCE_REINFORCE * RETROACTIVE_WEIGHT
        result = inject_retroactive(['directness', 'honesty'])
        assert result['strength_delta'] == expected_delta
        assert expected_delta < CO_OCCURRENCE_REINFORCE  # weaker than live

    def test_skips_unknown_concepts(self, test_db, monkeypatch):
        conn, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: conn)

        result = inject_retroactive(['directness', 'nonexistent-concept', 'honesty'])
        assert result['status'] == 'injected'
        assert 'nonexistent-concept' in result['skipped']
        assert result['connections_updated'] == 1  # only directness-honesty pair

    def test_skips_when_fewer_than_two_valid(self, test_db, monkeypatch):
        conn, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: conn)

        result = inject_retroactive(['directness', 'fake1', 'fake2'])
        assert result['status'] == 'skipped'
        assert 'only 1 valid concepts' in result['reason']

    def test_skips_all_unknown(self, test_db, monkeypatch):
        conn, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: conn)

        result = inject_retroactive(['fake1', 'fake2', 'fake3'])
        assert result['status'] == 'skipped'

    def test_logs_activation(self, test_db, monkeypatch):
        _, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: get_db(str(db_path)))

        inject_retroactive(['directness', 'honesty'], session='test-session')

        # Reopen connection to verify (inject_retroactive closes its own)
        verify = get_db(str(db_path))
        act = verify.execute(
            "SELECT * FROM activations WHERE session = 'retroactive-test-session'"
        ).fetchone()
        assert act is not None
        concepts = json.loads(act['concepts'])
        assert 'directness' in concepts
        assert 'honesty' in concepts
        verify.close()

    def test_handles_case_normalization(self, test_db, monkeypatch):
        _, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: get_db(str(db_path)))

        result = inject_retroactive(['Directness', 'HONESTY'])
        assert result['status'] == 'injected'

    def test_connection_is_committed(self, test_db, monkeypatch):
        _, db_path = test_db
        monkeypatch.setattr('retroactive.get_db', lambda: get_db(str(db_path)))

        inject_retroactive(['directness', 'building'])

        # Reopen to verify
        verify = get_db(str(db_path))
        row = verify.execute("""
            SELECT * FROM connections
            WHERE (source_id = 1 AND target_id = 4) OR (source_id = 4 AND target_id = 1)
        """).fetchone()
        assert row is not None
        assert row['strength'] > 0
        verify.close()
