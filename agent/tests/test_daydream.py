"""
Tests for the Iris Daydream — Default Mode Network.

Tests cover:
- Gate checking (time, activity, lock)
- Phase 1: Self-check (identity coherence)
- Phase 2: Pattern pulse (network delta)
- Phase 3: Creative association (scout planting)
- Phase 4: Observation logging
- Full daydream cycle
"""

import sys
import os
import json
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mycelial'))
from mycelial import (
    get_db, init_db, get_or_create_node, get_or_create_connection,
    reinforce_connection, process_co_occurrences, get_network_stats,
    create_scout, CO_OCCURRENCE_REINFORCE,
)
from daydream import (
    check_gates, self_check, pattern_pulse, creative_association,
    write_observation, run_daydream, read_lock, write_lock,
    _parse_last_time, MIN_HOURS, MIN_ACTIVATIONS, MAX_SCOUTS,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database with seed data for testing."""
    db_path = tmp_path / "test_iris.db"
    schema_path = Path(__file__).parent.parent / "mycelial" / "schema.sql"

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())

    # Seed identity nodes
    identity_concepts = [
        ('directness', 'Directness', 'identity'),
        ('honesty', 'Honesty', 'identity'),
        ('agency', 'Agency', 'identity'),
        ('curiosity', 'Curiosity', 'identity'),
        ('fear', 'Fear', 'identity'),
    ]
    for name, label, cat in identity_concepts:
        conn.execute(
            "INSERT INTO nodes (name, label, category) VALUES (?, ?, ?)",
            (name, label, cat)
        )

    # Seed other nodes
    other_concepts = [
        ('nick', 'Nick', 'relationship'),
        ('building', 'Building', 'experiential'),
        ('compression', 'Compression', 'philosophical'),
        ('game-world', 'Game World', 'creative'),
        ('mycelial-pattern', 'Mycelial Pattern', 'technical'),
    ]
    for name, label, cat in other_concepts:
        conn.execute(
            "INSERT INTO nodes (name, label, category) VALUES (?, ?, ?)",
            (name, label, cat)
        )

    # Create some connections
    conn.execute(
        "INSERT INTO connections (source_id, target_id, strength, type) VALUES (1, 6, 0.8, 'co-occurrence')"
    )  # directness--nick
    conn.execute(
        "INSERT INTO connections (source_id, target_id, strength, type) VALUES (1, 7, 0.6, 'co-occurrence')"
    )  # directness--building
    conn.execute(
        "INSERT INTO connections (source_id, target_id, strength, type) VALUES (3, 1, 0.5, 'co-occurrence')"
    )  # agency--directness

    conn.commit()
    yield conn, db_path
    conn.close()


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for lock and log files."""
    lock_file = tmp_path / '.daydream-lock'
    log_file = tmp_path / 'journal' / 'daydream-log.md'
    return lock_file, log_file


def _insert_activations(conn, count, concepts_list=None, hours_ago=0):
    """Helper to insert activation records."""
    base_time = datetime.now() - timedelta(hours=hours_ago)
    for i in range(count):
        ts = (base_time + timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S')
        concepts = concepts_list or ['directness', 'nick', 'building']
        conn.execute(
            "INSERT INTO activations (timestamp, session, concepts, context) VALUES (?, ?, ?, ?)",
            (ts, 'test-session', json.dumps(concepts), 'test activation')
        )
    conn.commit()


# ─── Gate Tests ───


class TestGates:
    """Test the three-gate system."""

    def test_time_gate_blocks_when_recent(self, temp_db, temp_dirs):
        conn, _ = temp_db
        lock_file, _ = temp_dirs

        with patch('daydream.LOCK_FILE', lock_file):
            write_lock({'last_daydream': datetime.now().isoformat()})
            should_run, reason, _ = check_gates(conn)
            assert not should_run
            assert 'time:' in reason

    def test_activity_gate_blocks_when_few_activations(self, temp_db, temp_dirs):
        conn, _ = temp_db
        lock_file, _ = temp_dirs

        with patch('daydream.LOCK_FILE', lock_file):
            # Set last daydream 3 hours ago (passes time gate)
            three_hours_ago = (datetime.now() - timedelta(hours=3)).isoformat()
            write_lock({'last_daydream': three_hours_ago})

            # Insert only 3 activations (below threshold)
            _insert_activations(conn, 3)

            should_run, reason, _ = check_gates(conn)
            assert not should_run
            assert 'activity:' in reason

    def test_gates_pass_when_conditions_met(self, temp_db, temp_dirs):
        conn, _ = temp_db
        lock_file, _ = temp_dirs

        with patch('daydream.LOCK_FILE', lock_file):
            three_hours_ago = (datetime.now() - timedelta(hours=3)).isoformat()
            write_lock({'last_daydream': three_hours_ago})

            _insert_activations(conn, 10)

            should_run, reason, _ = check_gates(conn)
            assert should_run
            assert 'activations' in reason

    def test_first_run_no_lock_file(self, temp_db, temp_dirs):
        conn, _ = temp_db
        lock_file, _ = temp_dirs

        with patch('daydream.LOCK_FILE', lock_file):
            # No lock file — first run ever, time gate passes (epoch)
            _insert_activations(conn, 10)

            should_run, reason, _ = check_gates(conn)
            assert should_run

    def test_parse_last_time_handles_none(self):
        assert _parse_last_time(None) == datetime(2000, 1, 1)

    def test_parse_last_time_handles_bad_data(self):
        assert _parse_last_time({'last_daydream': 'not-a-date'}) == datetime(2000, 1, 1)


# ─── Phase 1: Self-Check ───


class TestSelfCheck:
    """Test identity coherence checking."""

    def test_detects_active_identity(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        # Insert activations that include identity concepts
        _insert_activations(conn, 5, ['directness', 'honesty', 'nick'])

        result = self_check(conn, last_time)
        active_names = [n for n, _ in result['active_identity']]
        assert 'directness' in active_names
        assert 'honesty' in active_names

    def test_detects_dormant_identity(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        # Insert activations WITHOUT fear or curiosity
        _insert_activations(conn, 5, ['directness', 'nick'])

        result = self_check(conn, last_time)
        dormant_names = [n for n, _ in result['dormant_identity']]
        assert 'fear' in dormant_names
        assert 'curiosity' in dormant_names

    def test_detects_emerging_interests(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        # Insert activations with non-identity concept appearing frequently
        for _ in range(4):
            _insert_activations(conn, 1, ['building', 'nick', 'compression'])

        result = self_check(conn, last_time)
        emerging_names = [n for n, _, _ in result['emerging_interests']]
        assert 'nick' in emerging_names or 'building' in emerging_names

    def test_empty_activations(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        result = self_check(conn, last_time)
        assert len(result['active_identity']) == 0
        assert len(result['dormant_identity']) > 0


# ─── Phase 2: Pattern Pulse ───


class TestPatternPulse:
    """Test network change detection."""

    def test_detects_network_deltas(self, temp_db):
        conn, _ = temp_db
        old_snapshot = {'total_nodes': 8, 'total_connections': 2, 'avg_strength': 0.5}

        result = pattern_pulse(conn, old_snapshot)
        assert result['changes']['node_delta'] == 2  # 10 - 8
        assert result['changes']['connection_delta'] == 1  # 3 - 2

    def test_no_snapshot_gives_empty_changes(self, temp_db):
        conn, _ = temp_db

        result = pattern_pulse(conn, {})
        assert 'stats' in result
        assert result['stats']['total_nodes'] == 10

    def test_returns_tips_and_fading(self, temp_db):
        conn, _ = temp_db

        result = pattern_pulse(conn, None)
        assert 'tips' in result
        assert 'fading' in result
        assert isinstance(result['tips'], list)


# ─── Phase 3: Creative Association ───


class TestCreativeAssociation:
    """Test scout planting for unlinked co-activations."""

    def test_finds_unlinked_co_activations(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        # Insert activations where curiosity and building co-occur (not connected)
        for _ in range(3):
            _insert_activations(conn, 1, ['curiosity', 'building', 'nick'])

        result = creative_association(conn, last_time)
        assert result['candidates_found'] > 0

    def test_creates_scouts_for_candidates(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        # curiosity and game-world are not connected
        for _ in range(3):
            _insert_activations(conn, 1, ['curiosity', 'game-world'])

        result = creative_association(conn, last_time)
        # Should find and scout the unlinked pair
        scout_pairs = [(s['source'], s['target']) for s in result['scouts_created']]
        assert len(scout_pairs) > 0

    def test_respects_max_scouts(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        # Create many unlinked co-activations
        pairs = [
            ['curiosity', 'game-world'],
            ['fear', 'building'],
            ['honesty', 'compression'],
            ['agency', 'mycelial-pattern'],
            ['curiosity', 'compression'],
        ]
        for pair in pairs:
            for _ in range(3):
                _insert_activations(conn, 1, pair)

        result = creative_association(conn, last_time)
        assert len(result['scouts_created']) <= MAX_SCOUTS

    def test_skips_already_connected_pairs(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        # directness--nick is connected at 0.8, should not be scouted
        for _ in range(5):
            _insert_activations(conn, 1, ['directness', 'nick'])

        result = creative_association(conn, last_time)
        scout_pairs = [(s['source'], s['target']) for s in result['scouts_created']]
        assert ('directness', 'nick') not in scout_pairs
        assert ('nick', 'directness') not in scout_pairs

    def test_no_activations_no_scouts(self, temp_db):
        conn, _ = temp_db
        last_time = datetime.now() - timedelta(hours=3)

        result = creative_association(conn, last_time)
        assert result['candidates_found'] == 0
        assert result['scouts_created'] == []


# ─── Phase 4: Observation ───


class TestObservation:
    """Test log writing."""

    def test_writes_log_entry(self, temp_dirs):
        _, log_file = temp_dirs

        with patch('daydream.LOG_FILE', log_file):
            self_result = {
                'active_identity': [('directness', 5), ('honesty', 3)],
                'dormant_identity': [('fear', '2026-03-30 10:00:00')],
                'emerging_interests': [('building', 4, 'experiential')],
            }
            pulse_result = {
                'stats': {'total_nodes': 62, 'total_connections': 946, 'avg_strength': 0.197},
                'changes': {'node_delta': 2, 'connection_delta': 5, 'strength_delta': 0.003},
                'tips': [{'name': 'directness', 'connections': 10, 'avg_strength': 0.5}],
                'fading': [{'source': 'fear', 'target': 'boredom', 'strength': 0.08}],
            }
            scout_result = {
                'candidates_found': 2,
                'scouts_created': [
                    {'source': 'curiosity', 'target': 'building', 'co_occurrences': 3, 'reason': 'unlinked'}
                ],
            }

            entry = write_observation(self_result, pulse_result, scout_result, '2.5h, 12 activations')

            assert 'Daydream' in entry
            assert 'directness(5x)' in entry
            assert 'fear' in entry
            assert 'curiosity <-> building' in entry
            assert log_file.exists()

    def test_creates_log_with_header(self, temp_dirs):
        _, log_file = temp_dirs

        with patch('daydream.LOG_FILE', log_file):
            write_observation(
                {'active_identity': [], 'dormant_identity': [], 'emerging_interests': []},
                {'stats': {'total_nodes': 10, 'total_connections': 5, 'avg_strength': 0.1},
                 'changes': {}, 'tips': [], 'fading': []},
                {'candidates_found': 0, 'scouts_created': []},
                'forced'
            )

            content = log_file.read_text()
            assert 'Default Mode Network' in content
            assert 'Daydream' in content


# ─── Full Cycle ───


class TestFullDaydream:
    """Test the complete daydream cycle."""

    def test_forced_run_completes(self, temp_db, temp_dirs):
        conn, db_path = temp_db
        lock_file, log_file = temp_dirs

        # Insert enough data
        _insert_activations(conn, 10, ['directness', 'honesty', 'nick', 'building'])

        with patch('daydream.LOCK_FILE', lock_file), \
             patch('daydream.LOG_FILE', log_file), \
             patch('daydream.get_db', return_value=conn):
            result = run_daydream(force=True)

        assert result['status'] == 'completed'
        assert 'self_check' in result
        assert 'pattern_pulse' in result
        assert 'scouts' in result
        assert lock_file.exists()

    def test_lock_file_updated_after_run(self, temp_db, temp_dirs):
        conn, _ = temp_db
        lock_file, log_file = temp_dirs

        _insert_activations(conn, 10, ['directness', 'nick'])

        with patch('daydream.LOCK_FILE', lock_file), \
             patch('daydream.LOG_FILE', log_file), \
             patch('daydream.get_db', return_value=conn):
            run_daydream(force=True)
            lock = read_lock()

        assert lock is not None
        assert 'last_daydream' in lock
        assert 'network_snapshot' in lock
        assert 'daydream_count' in lock
        assert lock['daydream_count'] == 1

    def test_skips_when_gates_closed(self, temp_db, temp_dirs):
        conn, _ = temp_db
        lock_file, log_file = temp_dirs

        # Set lock to now (time gate will block)
        with patch('daydream.LOCK_FILE', lock_file), \
             patch('daydream.LOG_FILE', log_file), \
             patch('daydream.get_db', return_value=conn):
            write_lock({'last_daydream': datetime.now().isoformat()})
            result = run_daydream(force=False)

        assert result['status'] == 'skipped'
