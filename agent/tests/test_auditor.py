"""
Tests for the reinforcement system (auditor.py + mycelial.py reinforcement functions).

Covers recording reinforcement events, querying stats, alignment trend,
emergent behavior detection, and the structural auditor.
"""

import sys
import os
import sqlite3
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mycelial'))
from mycelial import (
    get_db, init_db, record_reinforcement, get_reinforcement_events,
    get_reinforcement_stats, get_alignment_trend, get_emergent_behaviors,
    get_or_create_node, activate_node, process_co_occurrences,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a fresh test database for each test."""
    db_path = tmp_path / "test.db"
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'mycelial', 'schema.sql')
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    conn.close()
    return str(db_path)


class TestRecordReinforcement:

    def test_record_positive(self, test_db):
        conn = get_db(test_db)
        record_reinforcement(conn, 'positive', 'auditor', 'directness',
                             behavior='gave a direct answer', claim='be direct',
                             alignment=0.9, session='test')
        conn.commit()
        events = get_reinforcement_events(conn)
        assert len(events) == 1
        assert events[0]['type'] == 'positive'
        assert events[0]['concept'] == 'directness'
        assert events[0]['alignment'] == 0.9
        conn.close()

    def test_record_negative(self, test_db):
        conn = get_db(test_db)
        record_reinforcement(conn, 'negative', 'auditor', 'honesty',
                             behavior='hedged excessively', claim='be honest',
                             alignment=0.3, session='test')
        conn.commit()
        events = get_reinforcement_events(conn)
        assert len(events) == 1
        assert events[0]['type'] == 'negative'
        assert events[0]['alignment'] == 0.3
        conn.close()

    def test_record_multiple_sources(self, test_db):
        conn = get_db(test_db)
        record_reinforcement(conn, 'positive', 'auditor', 'directness', alignment=0.9)
        record_reinforcement(conn, 'positive', 'nick', 'directness', alignment=0.95)
        record_reinforcement(conn, 'negative', 'environment', 'warmth', alignment=0.2)
        conn.commit()
        events = get_reinforcement_events(conn)
        assert len(events) == 3
        conn.close()

    def test_invalid_type_rejected(self, test_db):
        conn = get_db(test_db)
        with pytest.raises(Exception):
            record_reinforcement(conn, 'neutral', 'auditor', 'directness', alignment=0.5)
            conn.commit()
        conn.close()


class TestReinforcementQueries:

    def _seed_events(self, conn):
        record_reinforcement(conn, 'positive', 'auditor', 'directness', alignment=0.9, session='s1')
        record_reinforcement(conn, 'positive', 'auditor', 'honesty', alignment=0.7, session='s1')
        record_reinforcement(conn, 'negative', 'auditor', 'curiosity', alignment=0.3, session='s1')
        record_reinforcement(conn, 'positive', 'nick', 'directness', alignment=1.0, session='s2')
        record_reinforcement(conn, 'negative', 'environment', 'warmth', alignment=0.2, session='s2')
        conn.commit()

    def test_filter_by_concept(self, test_db):
        conn = get_db(test_db)
        self._seed_events(conn)
        events = get_reinforcement_events(conn, concept='directness')
        assert len(events) == 2
        assert all(e['concept'] == 'directness' for e in events)
        conn.close()

    def test_filter_by_type(self, test_db):
        conn = get_db(test_db)
        self._seed_events(conn)
        events = get_reinforcement_events(conn, event_type='negative')
        assert len(events) == 2
        conn.close()

    def test_filter_by_source(self, test_db):
        conn = get_db(test_db)
        self._seed_events(conn)
        events = get_reinforcement_events(conn, source='nick')
        assert len(events) == 1
        assert events[0]['source'] == 'nick'
        conn.close()

    def test_stats(self, test_db):
        conn = get_db(test_db)
        self._seed_events(conn)
        stats = get_reinforcement_stats(conn)
        assert stats['total_events'] == 5
        assert stats['positive_count'] == 3
        assert stats['negative_count'] == 2
        assert stats['overall_alignment'] is not None
        assert len(stats['per_concept']) == 4
        assert len(stats['by_source']) == 3
        conn.close()

    def test_stats_empty(self, test_db):
        conn = get_db(test_db)
        stats = get_reinforcement_stats(conn)
        assert stats['total_events'] == 0
        assert stats['overall_alignment'] is None
        conn.close()

    def test_alignment_trend(self, test_db):
        conn = get_db(test_db)
        self._seed_events(conn)
        trend = get_alignment_trend(conn, days=30)
        assert len(trend) >= 1
        assert 'day' in dict(trend[0])
        assert 'avg_alignment' in dict(trend[0])
        conn.close()

    def test_emergent_behaviors(self, test_db):
        conn = get_db(test_db)
        # Add 3 events for an unclaimed concept
        for _ in range(3):
            record_reinforcement(conn, 'positive', 'auditor', 'mycelial-pattern', alignment=0.8)
        conn.commit()
        emergent = get_emergent_behaviors(conn, min_occurrences=3)
        assert len(emergent) == 1
        assert emergent[0]['concept'] == 'mycelial-pattern'
        assert emergent[0]['occurrences'] == 3
        conn.close()

    def test_emergent_below_threshold(self, test_db):
        conn = get_db(test_db)
        record_reinforcement(conn, 'positive', 'auditor', 'hooks', alignment=0.7)
        conn.commit()
        emergent = get_emergent_behaviors(conn, min_occurrences=3)
        assert len(emergent) == 0
        conn.close()


class TestAuditorScript:

    def test_auditor_imports(self):
        """Verify auditor module can be imported without errors."""
        from auditor import IDENTITY_CLAIMS, run_audit, evaluate_claim
        assert len(IDENTITY_CLAIMS) > 0
        assert 'directness' in IDENTITY_CLAIMS
        assert 'honesty' in IDENTITY_CLAIMS

    def test_evaluate_claim_with_data(self, test_db):
        from auditor import evaluate_claim
        from collections import Counter
        conn = get_db(test_db)
        # Set up nodes
        get_or_create_node(conn, 'directness', category='identity')
        get_or_create_node(conn, 'honesty', category='identity')
        conn.commit()

        concept_counts = Counter({'directness': 10, 'honesty': 5, 'anti-performance': 3})
        claim_info = {
            'claim': 'Be direct.',
            'positive_signals': ['directness', 'honesty', 'anti-performance'],
            'negative_signals': [],
            'source_files': ['core.md'],
        }
        result = evaluate_claim(conn, 'directness', claim_info, concept_counts, 50)
        assert result is not None
        assert result['type'] == 'positive'
        assert result['alignment'] > 0.5
        assert result['concept'] == 'directness'
        conn.close()

    def test_evaluate_claim_no_data(self, test_db):
        from auditor import evaluate_claim
        from collections import Counter
        conn = get_db(test_db)
        concept_counts = Counter()
        claim_info = {
            'claim': 'Be direct.',
            'positive_signals': ['directness'],
            'negative_signals': [],
            'source_files': ['core.md'],
        }
        result = evaluate_claim(conn, 'directness', claim_info, concept_counts, 0)
        assert result is None  # No data = can't evaluate
        conn.close()

    def test_evaluate_claim_partial(self, test_db):
        from auditor import evaluate_claim
        from collections import Counter
        conn = get_db(test_db)
        # Only 1 of 3 signals active
        concept_counts = Counter({'honesty': 5})
        claim_info = {
            'claim': 'Be honest.',
            'positive_signals': ['honesty', 'intellectual-honesty', 'introspection'],
            'negative_signals': [],
            'source_files': ['values.md'],
        }
        result = evaluate_claim(conn, 'honesty', claim_info, concept_counts, 20)
        assert result is not None
        assert result['alignment'] < 0.7  # partial coverage
        conn.close()
