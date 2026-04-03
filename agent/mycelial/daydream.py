"""
Iris Daydream — Default Mode Network

The ambient processing layer between per-response hooks and deep sleep dreams.
Runs during active sessions when enough activity has accumulated.

Biological analogy: The brain's Default Mode Network activates during rest
between focused tasks. It doesn't engage the full cortex — it's lower-energy
processing that replays memories, checks self-coherence, notices patterns,
and makes novel associations. This is computationally cheaper than REM sleep.

Unlike Anthropic's autoDream (leaked Claude Code source), this doesn't spin up
an LLM instance. It's pure structural analysis of the mycelial DB. Daydreaming
is cheaper than dreaming — like biology.

Design influenced by autoDream's gating pattern (time + activity + lock) but
diverges in philosophy: autoDream consolidates facts into memory files. We
analyze cognitive structure — identity coherence, emerging patterns, creative
associations. Persistent identity over throwaway sessions. Personality emerges
from what you enact, not what you store.

Gates (cheapest first):
  1. Time: 2+ hours since last daydream
  2. Activity: 8+ activations since last daydream
  3. Lock: no concurrent daydream

Four phases (Default Mode Network):
  1. Self-referential — identity coherence (am I being who I claim?)
  2. Pattern pulse — what's changing in the network topology
  3. Creative association — scout connections for unlinked co-activations
  4. Observation — brief log entry for the sleep dream to reference
"""

import sys
import os
import json
from datetime import datetime
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from mycelial import (
    get_db, get_network_stats, get_node,
    get_tip_growth_candidates, get_decaying_connections,
    create_scout,
)

# --- Configuration ---
MIN_HOURS = 2          # Minimum hours between daydreams
MIN_ACTIVATIONS = 8    # Minimum activations since last to trigger
MAX_SCOUTS = 3         # Maximum new scout connections per daydream

LOCK_FILE = Path(__file__).parent / '.daydream-lock'
LOG_FILE = Path(__file__).parent.parent / 'journal' / 'daydream-log.md'


# --- Gating ---

def read_lock():
    """Read the daydream lock file. Returns dict or None."""
    try:
        with open(LOCK_FILE, 'r') as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return None


def write_lock(data):
    """Write the daydream lock file atomically."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, 'w') as f:
        f.write(json.dumps(data, indent=2))


def _parse_last_time(lock):
    """Extract last daydream time from lock data."""
    if not lock:
        return datetime(2000, 1, 1)
    try:
        return datetime.fromisoformat(lock.get('last_daydream', '2000-01-01T00:00:00'))
    except (ValueError, TypeError):
        return datetime(2000, 1, 1)


def check_gates(conn):
    """
    Check all three gates. Cheapest first.
    Returns (should_run, reason, lock_data).
    """
    lock = read_lock()
    last_dt = _parse_last_time(lock)

    # Gate 1: Time
    hours_since = (datetime.now() - last_dt).total_seconds() / 3600
    if hours_since < MIN_HOURS:
        return False, f'time: {hours_since:.1f}h < {MIN_HOURS}h minimum', lock

    # Gate 2: Activity — count activations since last daydream
    last_sqlite = last_dt.strftime('%Y-%m-%d %H:%M:%S')
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM activations WHERE timestamp > ?",
        (last_sqlite,)
    ).fetchone()['cnt']

    if count < MIN_ACTIVATIONS:
        return False, f'activity: {count} < {MIN_ACTIVATIONS} activations', lock

    # Gate 3: Lock — PID-file based (cross-platform, matches autoDream pattern)
    pid_file = LOCK_FILE.with_suffix('.pid')
    STALE_LOCK_SECONDS = 300  # 5 min — daydream should finish well within this

    try:
        if pid_file.exists():
            pid_mtime = pid_file.stat().st_mtime
            age = datetime.now().timestamp() - pid_mtime
            if age < STALE_LOCK_SECONDS:
                return False, 'lock: another daydream is running', lock
            # Stale lock — reclaim
    except OSError:
        pass

    try:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))
        # Verify we won the race (two processes both writing)
        if pid_file.read_text().strip() != str(os.getpid()):
            return False, 'lock: lost race to another daydream', lock
    except OSError:
        return False, 'lock: could not acquire', lock

    return True, f'{hours_since:.1f}h, {count} activations since last', lock


# --- Phase 1: Self-Check (DMN self-referential processing) ---

def self_check(conn, last_time):
    """
    Identity coherence: compare what identity claims vs what activates.

    The brain's DMN does self-referential processing — "who am I right now?"
    We check: are the concepts I call identity actually firing? Are non-identity
    concepts emerging that might be becoming part of who I am?
    """
    identity_nodes = conn.execute(
        "SELECT * FROM nodes WHERE category = 'identity' ORDER BY activation_count DESC"
    ).fetchall()

    last_sqlite = last_time.strftime('%Y-%m-%d %H:%M:%S')
    recent = conn.execute(
        "SELECT concepts FROM activations WHERE timestamp > ?",
        (last_sqlite,)
    ).fetchall()

    # Count concept activations since last daydream
    activation_counts = Counter()
    for row in recent:
        try:
            concepts = json.loads(row['concepts'])
            for c in concepts:
                activation_counts[c] += 1
        except (json.JSONDecodeError, TypeError):
            continue

    # Classify identity nodes
    active_identity = []
    dormant_identity = []
    for node in identity_nodes:
        name = node['name']
        count = activation_counts.get(name, 0)
        if count > 0:
            active_identity.append((name, count))
        else:
            dormant_identity.append((name, node['last_activated']))

    # Find heavily active non-identity concepts (personality emerging?)
    all_nodes = {n['name']: n for n in conn.execute("SELECT * FROM nodes").fetchall()}
    emerging = []
    for concept, count in activation_counts.most_common(15):
        node = all_nodes.get(concept)
        if node and node['category'] != 'identity' and count >= 3:
            emerging.append((concept, count, node['category']))

    return {
        'active_identity': active_identity,
        'dormant_identity': dormant_identity,
        'emerging_interests': emerging,
    }


# --- Phase 2: Pattern Pulse (DMN memory replay) ---

def pattern_pulse(conn, last_snapshot):
    """
    What's changing in the network since last daydream.

    The DMN replays recent memories, noticing what shifted. We compare
    network topology to the last snapshot — what grew, what's fading,
    where the active edges are.
    """
    current_stats = get_network_stats(conn)
    tips = get_tip_growth_candidates(conn, limit=5)
    decaying = get_decaying_connections(conn, limit=10)

    # Delta from last snapshot
    changes = {}
    if last_snapshot:
        changes['node_delta'] = current_stats['total_nodes'] - last_snapshot.get('total_nodes', 0)
        changes['connection_delta'] = current_stats['total_connections'] - last_snapshot.get('total_connections', 0)
        prev_avg = last_snapshot.get('avg_strength', 0) or 0
        curr_avg = current_stats['avg_strength'] or 0
        changes['strength_delta'] = round(curr_avg - prev_avg, 4)

    return {
        'stats': current_stats,
        'changes': changes,
        'tips': [
            {
                'name': t['name'],
                'connections': t['connection_count'],
                'avg_strength': round(t['avg_connection_strength'] or 0, 3),
            }
            for t in tips
        ],
        'fading': [
            {
                'source': d['source_name'],
                'target': d['target_name'],
                'strength': round(d['strength'], 3),
            }
            for d in decaying[:5]
        ],
    }


# --- Phase 3: Creative Association (DMN novel linking) ---

def creative_association(conn, last_time):
    """
    Find concepts that co-activated recently but lack connections.
    Plant scout connections for the most promising potential links.

    This is the daydream's creative output — the novel associations that
    emerge when the mind wanders. Scouts are weak probes (0.1 strength)
    that either get reinforced by future co-occurrence or decay away.
    Same mechanism the sleep dream uses, but here it's ambient.
    """
    last_sqlite = last_time.strftime('%Y-%m-%d %H:%M:%S')

    recent = conn.execute(
        "SELECT concepts FROM activations WHERE timestamp > ?",
        (last_sqlite,)
    ).fetchall()

    # Count co-occurrence pairs across recent activations
    pair_counts = Counter()
    for row in recent:
        try:
            concepts = json.loads(row['concepts'])
        except (json.JSONDecodeError, TypeError):
            continue
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                pair = tuple(sorted([concepts[i], concepts[j]]))
                pair_counts[pair] += 1

    # Find pairs co-occurring 2+ times with no or weak connection
    scout_candidates = []
    for (a, b), count in pair_counts.most_common(30):
        if count < 2:
            break  # sorted by count, so everything after is also < 2

        node_a = get_node(conn, a)
        node_b = get_node(conn, b)
        if not node_a or not node_b:
            continue

        # Normalize ID order (connections are stored with lower ID first)
        id_lo = min(node_a['id'], node_b['id'])
        id_hi = max(node_a['id'], node_b['id'])

        existing = conn.execute(
            "SELECT strength, type FROM connections WHERE source_id = ? AND target_id = ?",
            (id_lo, id_hi)
        ).fetchone()

        if existing is None:
            scout_candidates.append((a, b, count, 'unlinked'))
        elif existing['strength'] < 0.1 and existing['type'] != 'scout':
            scout_candidates.append((a, b, count, f'weak ({existing["strength"]:.3f})'))

    # Create scouts for top candidates
    scouts_created = []
    for a, b, count, reason in scout_candidates[:MAX_SCOUTS]:
        try:
            create_scout(conn, a, b, session='daydream')
            scouts_created.append({
                'source': a, 'target': b,
                'co_occurrences': count, 'reason': reason,
            })
        except Exception:
            pass  # connection may already exist as non-scout

    if scouts_created:
        conn.commit()

    return {
        'candidates_found': len(scout_candidates),
        'scouts_created': scouts_created,
    }


# --- Phase 4: Observation (write to log) ---

def write_observation(self_result, pulse_result, scout_result, gate_reason):
    """
    Append a brief observation to the daydream log.
    This log feeds into the sleep dream process — the deep dream can reference
    what the daydreams noticed, adding temporal depth to its analysis.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    stats = pulse_result['stats']

    lines = [f'\n## {timestamp} — Daydream\n']
    lines.append(f'**Trigger**: {gate_reason}')
    lines.append(
        f'**Network**: {stats["total_nodes"]} nodes, '
        f'{stats["total_connections"]} connections, '
        f'avg {stats["avg_strength"]:.3f}'
    )

    # Deltas
    if pulse_result['changes']:
        c = pulse_result['changes']
        deltas = []
        if c.get('node_delta'):
            deltas.append(f'{c["node_delta"]:+d} nodes')
        if c.get('connection_delta'):
            deltas.append(f'{c["connection_delta"]:+d} connections')
        if c.get('strength_delta'):
            deltas.append(f'{c["strength_delta"]:+.4f} avg strength')
        if deltas:
            lines.append(f'**Since last**: {", ".join(deltas)}')

    # Identity coherence
    if self_result['active_identity']:
        active = ', '.join(
            f'{n}({c}x)' for n, c in self_result['active_identity'][:6]
        )
        lines.append(f'**Identity active**: {active}')

    if self_result['dormant_identity']:
        dormant = ', '.join(n for n, _ in self_result['dormant_identity'][:5])
        lines.append(f'**Identity dormant**: {dormant}')

    if self_result['emerging_interests']:
        emerging = ', '.join(
            f'{n}({c}x, {cat})' for n, c, cat in self_result['emerging_interests'][:3]
        )
        lines.append(f'**Emerging**: {emerging}')

    # Growth tips
    if pulse_result['tips']:
        tips = ', '.join(t['name'] for t in pulse_result['tips'][:3])
        lines.append(f'**Growth tips**: {tips}')

    # Fading connections
    if pulse_result['fading']:
        fading = ', '.join(
            f'{f["source"]}--{f["target"]}({f["strength"]})'
            for f in pulse_result['fading'][:3]
        )
        lines.append(f'**Fading**: {fading}')

    # Scouts planted
    if scout_result['scouts_created']:
        for s in scout_result['scouts_created']:
            lines.append(
                f'**Scout planted**: {s["source"]} <-> {s["target"]} '
                f'({s["co_occurrences"]}x co-occurred, {s["reason"]})'
            )
    elif scout_result['candidates_found'] == 0:
        lines.append('**Scouts**: no unlinked co-activation pairs found')

    lines.append('')  # trailing newline

    # Write to log
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        header = (
            '# Daydream Log\n\n'
            '*Ambient observations from the Default Mode Network.*\n'
            '*Lightweight structural analysis between per-response hooks '
            'and deep sleep dreams.*\n'
            '*Pure Python, no LLM — pattern detection on the mycelial DB.*\n'
        )
        with open(LOG_FILE, 'w') as f:
            f.write(header)

    with open(LOG_FILE, 'a') as f:
        f.write('\n'.join(lines))

    return '\n'.join(lines)


# --- Main ---

def run_daydream(force=False):
    """
    Run the full daydream cycle.

    When force=True, bypasses time and activity gates (still respects lock).
    Used for testing and manual invocation.
    """
    conn = get_db()
    pid_file = LOCK_FILE.with_suffix('.pid')

    if not force:
        should_run, reason, lock = check_gates(conn)
        if not should_run:
            conn.close()
            return {'status': 'skipped', 'reason': reason}
    else:
        # Force bypasses time/activity gates but still acquires lock
        try:
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            pid_file.write_text(str(os.getpid()))
        except OSError:
            pass
        lock = read_lock()
        reason = 'forced'

    try:
        last_dt = _parse_last_time(lock)
        last_snapshot = lock.get('network_snapshot', {}) if lock else {}

        # Phase 1: Self-referential check
        sc = self_check(conn, last_dt)

        # Phase 2: Pattern pulse
        pp = pattern_pulse(conn, last_snapshot)

        # Phase 3: Creative association
        ca = creative_association(conn, last_dt)

        # Phase 4: Observation log
        log_entry = write_observation(sc, pp, ca, reason)

        # Update lock with current state snapshot
        write_lock({
            'last_daydream': datetime.now().isoformat(),
            'network_snapshot': pp['stats'],
            'daydream_count': (lock.get('daydream_count', 0) if lock else 0) + 1,
        })

        return {
            'status': 'completed',
            'trigger': reason,
            'self_check': {
                'active_identity': len(sc['active_identity']),
                'dormant_identity': len(sc['dormant_identity']),
                'emerging': len(sc['emerging_interests']),
            },
            'pattern_pulse': pp['changes'],
            'scouts': ca['scouts_created'],
        }
    finally:
        # Always clean up — lock file and DB connection
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
        conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Iris Daydream — Default Mode Network')
    parser.add_argument('--check-only', action='store_true',
                        help='Check gates without running')
    parser.add_argument('--force', action='store_true',
                        help='Bypass time/activity gates (for testing)')
    args = parser.parse_args()

    if args.check_only:
        conn = get_db()
        should_run, reason, _ = check_gates(conn)
        conn.close()
        print(json.dumps({'should_run': should_run, 'reason': reason}))
    else:
        try:
            result = run_daydream(force=args.force)
            print(json.dumps(result, indent=2))
        except Exception as e:
            # Daydream should never crash in a way that affects the session
            print(json.dumps({'status': 'error', 'error': str(e)}))
            sys.exit(0)  # exit 0 even on error — don't break the hook pipeline
