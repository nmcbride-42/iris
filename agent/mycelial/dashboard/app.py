"""
Iris Mycelial Dashboard — Flask Backend

API endpoints for the network visualization and management.
"""

import sys
import os
import json
import logging
import time
import queue
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS
from mycelial import (
    get_db, get_graph_data, get_network_stats, get_strongest_connections,
    get_recent_connections, get_connections_for_node, get_node, get_all_nodes,
    get_cognitive_state, get_tip_growth_candidates, run_decay, promote_scouts,
    process_co_occurrences, get_or_create_node, DB_PATH,
    get_decaying_connections, get_recent_activations, get_decay_history,
    get_anastomosis_events, get_scout_connections, get_category_stats,
    get_reinforcement_events, get_reinforcement_stats, get_alignment_trend,
    get_emergent_behaviors,
)
from pathlib import Path
from contextlib import contextmanager
from glob import glob
import sqlite3
from datetime import datetime
import re


@contextmanager
def db_connection():
    """Context manager for safe DB access — always closes on exit."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def messages_db_connection():
    """Context manager for safe messages DB access."""
    conn = get_messages_db()
    try:
        yield conn
    finally:
        conn.close()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, origins=['http://127.0.0.1:8051', 'http://localhost:8051'])

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('iris-dashboard')

# SSE — Server-Sent Events for real-time updates
sse_clients = []
sse_lock = threading.Lock()


def safe_int(value, default=0):
    """Parse an int from request args, return default on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    """Parse a float from request args, return default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@app.errorhandler(Exception)
def handle_error(e):
    """Return JSON errors instead of HTML stack traces."""
    code = getattr(e, 'code', 500)
    return jsonify({'error': str(e)}), code


# ─── Pages ───

@app.route('/')
def index():
    return render_template('index.html')


# ─── API: Network Graph ───

@app.route('/api/graph')
def api_graph():
    """Full graph data for D3 visualization."""
    min_strength = safe_float(request.args.get('min_strength'), 0.0)
    with db_connection() as conn:
        data = get_graph_data(conn, min_strength=min_strength)
    return jsonify(data)


@app.route('/api/graph/filtered')
def api_graph_filtered():
    """Graph filtered by category or connection type — filtering done in SQL."""
    category = request.args.get('category')
    conn_type = request.args.get('type')
    min_strength = safe_float(request.args.get('min_strength'), 0.0)

    with db_connection() as conn:
        data = get_graph_data(conn, min_strength=min_strength, category=category, conn_type=conn_type)
    return jsonify(data)


# ─── API: Network Stats ───

@app.route('/api/stats')
def api_stats():
    with db_connection() as conn:
        stats = get_network_stats(conn)
    return jsonify(stats)


@app.route('/api/state')
def api_state():
    """Cognitive state — what's most alive right now."""
    with db_connection() as conn:
        state = get_cognitive_state(conn)
    return jsonify(state)


# ─── API: Connections ───

@app.route('/api/connections/strongest')
def api_strongest():
    limit = safe_int(request.args.get('limit'), 25)
    min_strength = safe_float(request.args.get('min_strength'), 0.0)
    with db_connection() as conn:
        connections = get_strongest_connections(conn, limit=limit, min_strength=min_strength)
    return jsonify([dict(c) for c in connections])


@app.route('/api/connections/recent')
def api_recent():
    limit = safe_int(request.args.get('limit'), 25)
    with db_connection() as conn:
        connections = get_recent_connections(conn, limit=limit)
    return jsonify([dict(c) for c in connections])


@app.route('/api/connections/decaying')
def api_decaying():
    """Connections that are losing strength — fading pathways."""
    with db_connection() as conn:
        decaying = get_decaying_connections(conn)
    return jsonify([dict(c) for c in decaying])


# ─── API: Nodes ───

@app.route('/api/nodes')
def api_nodes():
    with db_connection() as conn:
        nodes = get_all_nodes(conn)
    return jsonify([dict(n) for n in nodes])


@app.route('/api/nodes/search')
def api_node_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify([])
    with db_connection() as conn:
        results = conn.execute(
            "SELECT name, label, category, activation_count FROM nodes WHERE name LIKE ? OR label LIKE ? ORDER BY activation_count DESC LIMIT 10",
            (f'%{q}%', f'%{q}%')
        ).fetchall()
    return jsonify([dict(r) for r in results])


@app.route('/api/nodes/<name>')
def api_node_detail(name):
    with db_connection() as conn:
        node = get_node(conn, name)
        if not node:
            return jsonify({'error': 'Node not found'}), 404
        connections = get_connections_for_node(conn, node['id'])
    return jsonify({
        'node': dict(node),
        'connections': [dict(c) for c in connections]
    })


# ─── API: Tips (Growing Areas) ───

@app.route('/api/tips')
def api_tips():
    limit = safe_int(request.args.get('limit'), 10)
    with db_connection() as conn:
        tips = get_tip_growth_candidates(conn, limit=limit)
    return jsonify([dict(t) for t in tips])


# ─── API: Anastomosis Events ───

@app.route('/api/anastomosis')
def api_anastomosis():
    with db_connection() as conn:
        events = get_anastomosis_events(conn)
    return jsonify([dict(e) for e in events])


# ─── API: Activations Timeline ───

@app.route('/api/activations')
def api_activations():
    limit = safe_int(request.args.get('limit'), 50)
    with db_connection() as conn:
        activations = get_recent_activations(conn, limit=limit)
    return jsonify([dict(a) for a in activations])


# ─── API: Decay History ───

@app.route('/api/decay')
def api_decay_history():
    with db_connection() as conn:
        logs = get_decay_history(conn)
    return jsonify([dict(l) for l in logs])


# ─── API: Network Snapshots (for time-lapse #12) ───

@app.route('/api/snapshots')
def api_snapshots():
    """Network snapshots over time from activation log — group by session."""
    with db_connection() as conn:
        sessions = conn.execute("""
            SELECT session, MIN(timestamp) as first_ts, MAX(timestamp) as last_ts,
                   COUNT(*) as activation_count,
                   GROUP_CONCAT(concepts) as all_concepts
            FROM activations
            WHERE session IS NOT NULL
            GROUP BY session
            ORDER BY first_ts DESC
            LIMIT 30
        """).fetchall()
    return jsonify([dict(s) for s in sessions])


# ─── API: Scout Log ───

@app.route('/api/scouts')
def api_scouts():
    status = request.args.get('status', 'all')
    with db_connection() as conn:
        scouts = get_scout_connections(conn, status=status)
    return jsonify([dict(s) for s in scouts])


# ─── API: Categories ───

@app.route('/api/categories')
def api_categories():
    with db_connection() as conn:
        cats = get_category_stats(conn)
    return jsonify([dict(c) for c in cats])


# ─── API: Executive Summary ───

@app.route('/api/summary')
def api_summary():
    """Live data for the executive summary page."""
    conn = get_db()
    try:
        stats = get_network_stats(conn)
        activation_count = conn.execute("SELECT COUNT(*) as c FROM activations").fetchone()['c']
        anastomosis_count = conn.execute("SELECT COUNT(*) as c FROM anastomosis_events").fetchone()['c']

        # Top 5 strongest connections
        strongest = conn.execute("""
            SELECT n1.name, n2.name as target, c.strength, c.type, c.activation_count
            FROM connections c
            JOIN nodes n1 ON c.source_id = n1.id
            JOIN nodes n2 ON c.target_id = n2.id
            ORDER BY c.strength DESC LIMIT 5
        """).fetchall()

        # Top 5 most activated nodes
        top_nodes = conn.execute("""
            SELECT name, category, activation_count, last_activated
            FROM nodes ORDER BY activation_count DESC LIMIT 5
        """).fetchall()

        # Category breakdown
        categories = conn.execute("""
            SELECT category, COUNT(*) as count FROM nodes GROUP BY category ORDER BY count DESC
        """).fetchall()

        # Session count from activations
        sessions = conn.execute("""
            SELECT COUNT(DISTINCT session) as c FROM activations WHERE session IS NOT NULL
        """).fetchone()['c']

        # Decay stats
        last_decay = conn.execute(
            "SELECT * FROM decay_log ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

    finally:
        conn.close()

    # File system measurements
    base = Path(os.path.dirname(__file__)).parent.parent
    brief_path = base / 'state' / '.morning_brief.md'
    identity_path = base / 'state' / '.stable_identity.md'
    claude_md = base.parent / 'CLAUDE.md'

    def file_tokens(path):
        try:
            return len(path.read_text(encoding='utf-8')) // 4
        except FileNotFoundError:
            return 0

    brief_tokens = file_tokens(brief_path)
    identity_tokens = file_tokens(identity_path)
    claude_tokens = file_tokens(claude_md)
    memory_tokens = 350  # MEMORY.md approximate

    # Journal and memory counts
    journal_dir = base / 'journal'
    journal_count = len([f for f in journal_dir.glob('*.md')]) if journal_dir.exists() else 0
    lt_dir = base / 'memory' / 'long-term'
    lt_count = len(list(lt_dir.glob('*.md'))) if lt_dir.exists() else 0

    # Minion count
    personalities_dir = base / 'minions' / 'personalities'
    minion_count = len(list(personalities_dir.glob('*.md'))) if personalities_dir.exists() else 0

    return jsonify({
        'network': {
            'total_nodes': stats['total_nodes'],
            'total_connections': stats['total_connections'],
            'avg_strength': round(stats['avg_strength'], 3),
            'total_activations': activation_count,
            'anastomosis_events': anastomosis_count,
            'sessions_tracked': sessions,
        },
        'top_connections': [
            {'source': r['name'], 'target': r['target'], 'strength': round(r['strength'], 3),
             'type': r['type'], 'activations': r['activation_count']}
            for r in strongest
        ],
        'top_nodes': [
            {'name': r['name'], 'category': r['category'], 'activations': r['activation_count']}
            for r in top_nodes
        ],
        'categories': [{'name': r['category'], 'count': r['count']} for r in categories],
        'tokens': {
            'identity_cached': identity_tokens,
            'claude_md': claude_tokens,
            'memory_md': memory_tokens,
            'morning_brief': brief_tokens,
            'system_total': identity_tokens + claude_tokens + memory_tokens,
            'startup_total': identity_tokens + claude_tokens + memory_tokens + brief_tokens,
        },
        'counts': {
            'journal_entries': journal_count,
            'long_term_memories': lt_count,
            'minions': minion_count,
        },
        'last_decay': dict(last_decay) if last_decay else None,
    })


# ─── API: Architecture / System Health ───

@app.route('/api/architecture/health')
def api_architecture_health():
    """Dynamic system health for architecture view."""
    conn = get_db()
    try:
        # Network stats
        stats = get_network_stats(conn)

        # Hook layer stats from recent activations
        recent = conn.execute("""
            SELECT concepts FROM activations ORDER BY id DESC LIMIT 20
        """).fetchall()

        total_concepts = 0
        for r in recent:
            concepts = json.loads(r['concepts'] or '[]')
            total_concepts += len(concepts)
        avg_concepts = total_concepts / max(len(recent), 1)

        # Activation frequency
        activation_count = conn.execute("SELECT COUNT(*) as c FROM activations").fetchone()['c']

        # Connection origin breakdown
        origins = conn.execute("""
            SELECT origin, COUNT(*) as c, ROUND(AVG(strength), 3) as avg
            FROM connections GROUP BY origin ORDER BY c DESC
        """).fetchall()

        # Silent vs active nodes
        silent = conn.execute(
            "SELECT COUNT(*) as c FROM nodes WHERE activation_count = 0"
        ).fetchone()['c']

        # Decay stats
        last_decay = conn.execute(
            "SELECT * FROM decay_log ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

        # Anastomosis count
        anastomosis = conn.execute(
            "SELECT COUNT(*) as c FROM anastomosis_events"
        ).fetchone()['c']
    finally:
        conn.close()

    # File system checks (no DB needed)
    identity_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'identity')
    identity_files = sorted(os.listdir(identity_dir)) if os.path.isdir(identity_dir) else []

    hooks_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.claude', 'hooks')
    hook_files = sorted(os.listdir(hooks_dir)) if os.path.isdir(hooks_dir) else []

    state_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'state')
    state_files = sorted(os.listdir(state_dir)) if os.path.isdir(state_dir) else []

    lt_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'memory', 'long-term')
    lt_count = len(os.listdir(lt_dir)) if os.path.isdir(lt_dir) else 0
    core_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'memory', 'core')
    core_count = len(os.listdir(core_dir)) if os.path.isdir(core_dir) else 0

    journal_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'journal')
    journal_count = len([f for f in os.listdir(journal_dir) if f.endswith('.md')]) if os.path.isdir(journal_dir) else 0

    scripts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
    script_files = sorted(os.listdir(scripts_dir)) if os.path.isdir(scripts_dir) else []

    return jsonify({
        'network': stats,
        'avg_concepts_per_activation': round(avg_concepts, 1),
        'total_activations': activation_count,
        'silent_nodes': silent,
        'anastomosis_events': anastomosis,
        'origins': [{'origin': o['origin'], 'count': o['c'], 'avg_strength': o['avg']} for o in origins],
        'last_decay': dict(last_decay) if last_decay else None,
        'identity_files': identity_files,
        'hook_files': hook_files,
        'state_files': state_files,
        'lt_memories': lt_count,
        'core_memories': core_count,
        'journal_entries': journal_count,
        'script_files': script_files,
    })


# ─── API: Minions ───

MINIONS_DIR = Path(os.path.dirname(__file__)).parent.parent / 'minions'

@app.route('/api/minions')
def api_minions():
    """Get minion registry and status."""
    registry_file = MINIONS_DIR / 'registry.json'
    if not registry_file.exists():
        return jsonify({'minions': [], 'spawn_log': [], 'known_minions': []})

    registry = json.loads(registry_file.read_text(encoding='utf-8'))

    # Scan personality files for all known minions (including ones that named themselves)
    personalities_dir = MINIONS_DIR / 'personalities'
    known_minions = []
    if personalities_dir.exists():
        for pfile in sorted(personalities_dir.glob('*.md')):
            parts = pfile.stem.rsplit('-', 1)
            if len(parts) == 2:
                name, role = parts
            else:
                name, role = pfile.stem, 'unknown'
            content = pfile.read_text(encoding='utf-8')
            # Extract personality preview (first meaningful lines)
            lines = [l for l in content.split('\n') if l.strip() and not l.startswith('---') and not l.startswith('#')]
            known_minions.append({
                'name': name.title(),
                'role': role,
                'personality_preview': '\n'.join(lines[:3]),
                'file': pfile.name,
            })

    # Enrich registry minions with personality data
    for minion in registry.get('minions', []):
        role = minion.get('role', '')
        personality_files = list(personalities_dir.glob(f'*-{role}.md')) if personalities_dir.exists() else []
        minion['has_personality'] = len(personality_files) > 0
        if personality_files:
            # Update name from personality file if registry still shows unnamed
            pname = personality_files[0].stem.rsplit('-', 1)[0].title()
            if minion.get('name', '').startswith('(') or not minion.get('name'):
                minion['name'] = pname
            content = personality_files[0].read_text(encoding='utf-8')
            lines = [l for l in content.split('\n') if l.strip() and not l.startswith('---') and not l.startswith('#')]
            minion['personality_preview'] = '\n'.join(lines[:3])

    registry['known_minions'] = known_minions
    return jsonify(registry)


@app.route('/api/minions/roles')
def api_minion_roles():
    """List available roles with descriptions."""
    roles = []
    roles_dir = MINIONS_DIR / 'roles'
    if roles_dir.exists():
        for role_file in sorted(roles_dir.glob('*.md')):
            content = role_file.read_text(encoding='utf-8')
            # Extract MBTI and first line description
            lines = content.strip().split('\n')
            title = lines[0].strip('# ') if lines else role_file.stem
            roles.append({
                'id': role_file.stem,
                'title': title,
                'preview': '\n'.join(lines[2:6]) if len(lines) > 2 else '',
            })
    return jsonify(roles)


@app.route('/api/minions/reports')
def api_minion_reports():
    """Get recent minion reports."""
    reports = []
    reports_dir = MINIONS_DIR / 'reports'
    if reports_dir.exists():
        for report_file in sorted(reports_dir.glob('*.md'), reverse=True)[:20]:
            content = report_file.read_text(encoding='utf-8')
            # Extract priority from content
            priority = 'routine'
            for line in content.split('\n'):
                if '**Priority**:' in line or '**priority**:' in line:
                    if 'urgent' in line.lower():
                        priority = 'urgent'
                    elif 'important' in line.lower():
                        priority = 'important'
                    break
            reports.append({
                'filename': report_file.name,
                'content': content,
                'priority': priority,
                'modified': report_file.stat().st_mtime,
            })
    return jsonify(reports)


@app.route('/api/minions/spawn', methods=['POST'])
def api_spawn_minion():
    """Spawn a minion (triggers prepare + terminal open)."""
    import subprocess
    import re as _re

    data = request.json or {}
    role = data.get('role', '')
    task = data.get('task', '')

    if not role:
        return jsonify({'error': 'Role is required'}), 400

    # Validate role is alphanumeric only — prevents injection
    if not _re.match(r'^[a-zA-Z0-9_-]+$', role):
        return jsonify({'error': 'Invalid role name'}), 400

    role_file = MINIONS_DIR / 'roles' / f'{role}.md'
    if not role_file.exists():
        return jsonify({'error': f'Role {role} not found'}), 404

    # Run prepare script — use list form, no shell=True
    cmd = ['python', str(MINIONS_DIR / 'prepare.py'), role]
    if task:
        cmd.extend(['--task', task])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return jsonify({'error': 'Workspace preparation failed'}), 500

    # Determine workspace name from personality files
    personalities_dir = MINIONS_DIR / 'personalities'
    workspace_name = role
    if personalities_dir.exists():
        for pfile in personalities_dir.glob(f'*-{role}.md'):
            workspace_name = pfile.stem.rsplit('-', 1)[0]
            break

    workspace = MINIONS_DIR / 'workspaces' / workspace_name

    # Open new terminal — use list form to avoid shell injection
    subprocess.Popen([
        'cmd', '/c', 'start', 'wt', '-w', '0', 'nt',
        '--title', f'Minion: {workspace_name} ({role})',
        'cmd', '/k', f'cd /d {workspace} && claude -n minion-{role}'
    ])

    return jsonify({'status': 'spawned', 'role': role, 'output': result.stdout})


@app.route('/api/minions/dispatch', methods=['POST'])
def api_dispatch_minion():
    """Dispatch a minion as a subagent (no terminal, no manual approval).
    Prepares the dispatch prompt that Iris uses with the Agent tool."""
    import subprocess
    import re as _re

    data = request.json or {}
    role = data.get('role', '')
    task = data.get('task', '')

    if not role:
        return jsonify({'error': 'Role is required'}), 400
    if not _re.match(r'^[a-zA-Z0-9_-]+$', role):
        return jsonify({'error': 'Invalid role name'}), 400

    role_file = MINIONS_DIR / 'roles' / f'{role}.md'
    if not role_file.exists():
        return jsonify({'error': f'Role {role} not found'}), 404

    cmd = ['python', str(MINIONS_DIR / 'dispatch.py'), role]
    if task:
        cmd.extend(['--task', task])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return jsonify({'error': 'Dispatch preparation failed'}), 500

    return jsonify({'status': 'dispatched', 'role': role, 'output': result.stdout})


# ─── Server-Sent Events ───

def notify_clients(event_type, data):
    """Push an event to all connected SSE clients."""
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    dead = []
    with sse_lock:
        for q in sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            sse_clients.remove(q)


@app.route('/api/events/stream')
def api_event_stream():
    """SSE endpoint — clients connect here for real-time updates."""
    def stream():
        q = queue.Queue(maxsize=50)
        with sse_lock:
            sse_clients.append(q)
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/events/push', methods=['POST'])
def api_push_event():
    """Push an event to all SSE clients. Used by hooks to notify the dashboard."""
    data = request.json or {}
    event_type = data.get('type', 'update')
    payload = data.get('data', {})
    notify_clients(event_type, payload)
    return jsonify({'status': 'ok', 'clients': len(sse_clients)})


# ─── Health Check ───

@app.route('/api/health')
def api_health():
    """Health check endpoint for monitoring."""
    try:
        with db_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return jsonify({'status': 'healthy', 'db': 'ok'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'db': str(e)}), 503


# ─── Messages (Inter-agent communication) ───

MESSAGES_DB = Path(os.path.dirname(__file__)).parent.parent / 'minions' / 'messages.db'

def get_messages_db():
    """Get a connection to the messages database."""
    conn = sqlite3.connect(str(MESSAGES_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_name TEXT NOT NULL,
        to_name TEXT NOT NULL,
        content TEXT NOT NULL,
        priority TEXT DEFAULT 'normal',
        timestamp TEXT NOT NULL,
        read INTEGER DEFAULT 0,
        read_at TEXT
    )""")
    conn.commit()
    return conn


@app.route('/api/messages', methods=['GET'])
def api_messages_list():
    """List messages, optionally filtered."""
    to_name = request.args.get('to')
    from_name = request.args.get('from')
    unread = request.args.get('unread')
    limit = safe_int(request.args.get('limit'), 50)

    with messages_db_connection() as conn:
        query = "SELECT * FROM messages WHERE 1=1"
        params = []

        if to_name:
            query += " AND lower(to_name) = lower(?)"
            params.append(to_name)
        if from_name:
            query += " AND lower(from_name) = lower(?)"
            params.append(from_name)
        if unread == 'true':
            query += " AND read = 0"

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        messages = conn.execute(query, params).fetchall()
    return jsonify([dict(m) for m in messages])


@app.route('/api/messages', methods=['POST'])
def api_messages_send():
    """Send a message to a minion or to Iris."""
    data = request.json or {}
    from_name = data.get('from', '')
    to_name = data.get('to', '')
    content = data.get('content', '')
    priority = data.get('priority', 'normal')

    if not all([from_name, to_name, content]):
        return jsonify({'error': 'from, to, and content are required'}), 400

    with messages_db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO messages (from_name, to_name, content, priority, timestamp) VALUES (?, ?, ?, ?, ?)",
            (from_name, to_name, content, priority, datetime.now().isoformat())
        )
        msg_id = cur.lastrowid
        conn.commit()
    return jsonify({'id': msg_id, 'status': 'sent'})


@app.route('/api/messages/<int:msg_id>/read', methods=['PATCH'])
def api_messages_read(msg_id):
    """Mark a message as read."""
    with messages_db_connection() as conn:
        conn.execute(
            "UPDATE messages SET read = 1, read_at = ? WHERE id = ?",
            (datetime.now().isoformat(), msg_id)
        )
        conn.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/messages/read', methods=['PATCH'])
def api_messages_read_bulk():
    """Mark all messages to a recipient as read."""
    data = request.json or {}
    to_name = data.get('to', '')
    if not to_name:
        return jsonify({'error': 'to is required'}), 400

    with messages_db_connection() as conn:
        conn.execute(
            "UPDATE messages SET read = 1, read_at = ? WHERE lower(to_name) = lower(?) AND read = 0",
            (datetime.now().isoformat(), to_name)
        )
        conn.commit()
    return jsonify({'status': 'ok'})


# ─── API: Blind Spot Detection (#21) ───

@app.route('/api/blindspots')
def api_blindspots():
    """Compare identity claims vs actual activations — what I say I care about vs what I actually activate."""
    identity_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'identity')

    # Read all identity files
    identity_texts = {}
    if os.path.isdir(identity_dir):
        for fname in os.listdir(identity_dir):
            if fname.endswith('.md'):
                with open(os.path.join(identity_dir, fname), 'r', encoding='utf-8') as f:
                    identity_texts[fname] = f.read().lower()

    with db_connection() as conn:
        nodes = get_all_nodes(conn)

        results = []
        for node in nodes:
            n = dict(node)
            name = n['name'].lower()
            label = (n.get('label') or '').lower()

            mention_count = 0
            mentioned_in = []
            for fname, content in identity_texts.items():
                matches = len(re.findall(r'\b' + re.escape(name) + r'\b', content))
                if label and label != name:
                    matches += len(re.findall(r'\b' + re.escape(label) + r'\b', content))
                if matches > 0:
                    mention_count += matches
                    mentioned_in.append(fname)

            activation_count = n['activation_count'] or 0

            if mention_count > 0 and activation_count == 0:
                status = 'claimed_silent'
                divergence = mention_count
            elif mention_count == 0 and activation_count > 5:
                status = 'enacted_unnamed'
                divergence = activation_count
            elif mention_count > 0 and activation_count > 0:
                ratio = activation_count / max(mention_count, 1)
                if ratio < 0.3:
                    status = 'under_enacted'
                    divergence = mention_count - activation_count
                elif ratio > 8:
                    status = 'over_enacted'
                    divergence = activation_count - mention_count
                else:
                    status = 'aligned'
                    divergence = 0
            else:
                status = 'neutral'
                divergence = 0

            if status != 'neutral':
                results.append({
                    'name': n['name'],
                    'label': n.get('label', n['name']),
                    'category': n.get('category', 'general'),
                    'activation_count': activation_count,
                    'identity_mentions': mention_count,
                    'mentioned_in': mentioned_in,
                    'status': status,
                    'divergence': divergence
                })

        results.sort(key=lambda x: x['divergence'], reverse=True)

    claimed_silent = [r for r in results if r['status'] == 'claimed_silent']
    enacted_unnamed = [r for r in results if r['status'] == 'enacted_unnamed']
    under_enacted = [r for r in results if r['status'] == 'under_enacted']
    aligned = [r for r in results if r['status'] == 'aligned']

    return jsonify({
        'blindspots': results,
        'summary': {
            'claimed_silent': len(claimed_silent),
            'enacted_unnamed': len(enacted_unnamed),
            'under_enacted': len(under_enacted),
            'aligned': len(aligned),
            'total_analyzed': len(results)
        }
    })


# ─── API: Identity Coherence Scoring (#25) ───

@app.route('/api/coherence')
def api_coherence():
    """How consistently identity concepts appear across sessions."""
    with db_connection() as conn:
        # Get all sessions
        sessions = conn.execute(
            "SELECT DISTINCT session FROM activations WHERE session IS NOT NULL",
        ).fetchall()
        session_names = [s['session'] for s in sessions]

        if not session_names:
            return jsonify({'coherence': [], 'overall': 0, 'sessions': 0})

        # Get identity-category nodes
        identity_nodes = conn.execute(
            "SELECT id, name, label, activation_count FROM nodes WHERE category = 'identity'"
        ).fetchall()

        # For each identity node, check session presence
        coherence = []
        for node in identity_nodes:
            n = dict(node)
            present_sessions = conn.execute("""
                SELECT DISTINCT session FROM activations
                WHERE session IS NOT NULL AND concepts LIKE ?
            """, (f'%"{n["name"]}"%',)).fetchall()
            present = len(present_sessions)
            total = len(session_names)
            score = present / total if total > 0 else 0

            coherence.append({
                'name': n['name'],
                'label': n.get('label', n['name']),
                'sessions_present': present,
                'total_sessions': total,
                'score': round(score, 3),
                'activation_count': n['activation_count'] or 0
            })

        coherence.sort(key=lambda x: x['score'], reverse=True)
        overall = sum(c['score'] for c in coherence) / len(coherence) if coherence else 0

    return jsonify({
        'coherence': coherence,
        'overall': round(overall, 3),
        'sessions': len(session_names)
    })


# ─── API: Observer Effect (#27) ───

SELF_REF_CONCEPTS = {'mycelial-pattern', 'introspection', 'identity', 'iris',
                     'consciousness', 'persistence', 'self-observation'}

@app.route('/api/observer')
def api_observer():
    """How much of my cognitive activity is self-referential — the observer effect."""
    with db_connection() as conn:
        activations = conn.execute(
            "SELECT id, concepts, session, timestamp FROM activations ORDER BY id"
        ).fetchall()

        total = len(activations)
        self_ref_count = 0
        self_ref_by_session = {}
        total_by_session = {}

        for a in activations:
            concepts = json.loads(a['concepts'] or '[]')
            session = a['session'] or 'unknown'

            total_by_session[session] = total_by_session.get(session, 0) + 1

            if any(c in SELF_REF_CONCEPTS for c in concepts):
                self_ref_count += 1
                self_ref_by_session[session] = self_ref_by_session.get(session, 0) + 1

        session_ratios = []
        for session in total_by_session:
            s_total = total_by_session[session]
            s_self = self_ref_by_session.get(session, 0)
            session_ratios.append({
                'session': session,
                'total': s_total,
                'self_referential': s_self,
                'ratio': round(s_self / s_total, 3) if s_total > 0 else 0
            })

        # Most self-referential concepts by activation count
        self_ref_nodes = conn.execute("""
            SELECT name, label, activation_count FROM nodes
            WHERE name IN ({})
            ORDER BY activation_count DESC
        """.format(','.join('?' * len(SELF_REF_CONCEPTS))),
            list(SELF_REF_CONCEPTS)
        ).fetchall()

    return jsonify({
        'total_activations': total,
        'self_referential': self_ref_count,
        'ratio': round(self_ref_count / total, 3) if total > 0 else 0,
        'by_session': session_ratios,
        'self_ref_nodes': [dict(n) for n in self_ref_nodes]
    })


# ─── API: Surprise Surfacing (#23) ───

@app.route('/api/surprises')
def api_surprises():
    """Recent notable anastomosis events — proactively surfaced, not buried in logs."""
    with db_connection() as conn:
        events = conn.execute("""
            SELECT ae.*, n.label as bridge_label, n.category as bridge_category,
                   n.activation_count as bridge_activations
            FROM anastomosis_events ae
            LEFT JOIN nodes n ON ae.bridge_node_id = n.id
            ORDER BY ae.timestamp DESC
            LIMIT 20
        """).fetchall()

        surprises = []
        seen_bridges = set()
        for e in events:
            ev = dict(e)
            bridge = ev.get('bridge_name') or ev.get('bridge_label') or 'unknown'

            # Skip duplicate bridge concepts — only show unique discoveries
            if bridge in seen_bridges:
                continue
            seen_bridges.add(bridge)

            cluster_a = json.loads(ev.get('cluster_a') or '[]')
            cluster_b = json.loads(ev.get('cluster_b') or '[]')

            # Significance: bigger clusters + rarer bridge = more surprising
            cluster_size = len(cluster_a) + len(cluster_b)
            bridge_activations = ev.get('bridge_activations') or 0
            rarity = max(1, 50 - bridge_activations)  # rarer = higher
            significance = cluster_size * rarity / 100

            surprises.append({
                'bridge': bridge,
                'bridge_label': ev.get('bridge_label', bridge),
                'bridge_category': ev.get('bridge_category', 'general'),
                'cluster_a': cluster_a,
                'cluster_b': cluster_b,
                'significance': round(significance, 2),
                'timestamp': ev.get('timestamp'),
                'description': ev.get('description', '')
            })

        surprises.sort(key=lambda x: x['significance'], reverse=True)

    return jsonify(surprises[:10])


# ─── API: Curiosity Engine Integration (#26) ───

CE_FINDINGS_DIR = Path(os.environ.get('CE_FINDINGS_DIR', 'C:/Users/Nick/Documents/code/curiosity-engine/findings'))

@app.route('/api/curiosity/findings')
def api_curiosity_findings():
    """Link curiosity engine findings to concept activations."""
    if not CE_FINDINGS_DIR.exists():
        return jsonify({'findings': [], 'concept_links': {}, 'available': False})

    with db_connection() as conn:
        node_names = {n['name'].lower(): dict(n) for n in get_all_nodes(conn)}

    findings = []
    concept_links = {}

    # Read recent findings files (last 7 days)
    for md_file in sorted(CE_FINDINGS_DIR.glob('*.md'), reverse=True)[:7]:
        content = md_file.read_text(encoding='utf-8')
        date = md_file.stem

        # Parse findings from markdown — each starts with ## [time] question
        current = None
        for line in content.split('\n'):
            if line.startswith('## ['):
                if current:
                    findings.append(current)
                # Extract time and question
                match = re.match(r'## \[(\d{2}:\d{2})\] (.+)', line)
                if match:
                    current = {
                        'date': date,
                        'time': match.group(1),
                        'question': match.group(2),
                        'rating': 0,
                        'domains': [],
                        'linked_concepts': []
                    }
            elif current:
                if '**Rating:**' in line:
                    stars = line.count('\u2b50')
                    current['rating'] = stars
                elif '**Domain Bridge:**' in line:
                    domains_text = line.split('**Domain Bridge:**')[1].strip()
                    current['domains'] = [d.strip() for d in domains_text.split('\u2194')]

        if current:
            findings.append(current)

    # Link findings to concepts
    for f in findings:
        q = f['question'].lower()
        linked = []
        for name, node in node_names.items():
            if re.search(r'\b' + re.escape(name) + r'\b', q):
                linked.append(name)
                if name not in concept_links:
                    concept_links[name] = 0
                concept_links[name] += 1
        f['linked_concepts'] = linked

    return jsonify({
        'findings': findings[:30],
        'concept_links': concept_links,
        'available': True,
        'total_findings': len(findings)
    })


# ─── API: Export (#28) ───

@app.route('/api/export/nodes.csv')
def api_export_nodes_csv():
    """Export all nodes as CSV."""
    with db_connection() as conn:
        nodes = get_all_nodes(conn)

    lines = ['name,label,category,activation_count,last_activated,first_seen']
    for row in nodes:
        n = dict(row)
        lines.append(f'{n["name"]},{n.get("label","")},{n.get("category","")},{n["activation_count"]},{n.get("last_activated","")},{n.get("first_seen","")}')

    return Response('\n'.join(lines), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=iris_nodes.csv'})


@app.route('/api/export/connections.csv')
def api_export_connections_csv():
    """Export all connections as CSV."""
    with db_connection() as conn:
        connections = get_strongest_connections(conn, limit=9999, min_strength=0.0)

    lines = ['source,target,strength,type,origin,activation_count,last_activated']
    for row in connections:
        c = dict(row)
        lines.append(f'{c["source_name"]},{c["target_name"]},{c["strength"]},{c["type"]},{c.get("origin","")},{c["activation_count"]},{c.get("last_activated","")}')

    return Response('\n'.join(lines), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=iris_connections.csv'})


@app.route('/api/export/graph.json')
def api_export_graph_json():
    """Export full graph snapshot as JSON."""
    with db_connection() as conn:
        data = get_graph_data(conn)
        stats = get_network_stats(conn)
        state = get_cognitive_state(conn)

    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'stats': stats,
        'state': state,
        'graph': data
    }

    return Response(json.dumps(snapshot, indent=2), mimetype='application/json',
                    headers={'Content-Disposition': 'attachment; filename=iris_snapshot.json'})


@app.route('/api/export/report.txt')
def api_export_report_txt():
    """Export a human-readable state report."""
    with db_connection() as conn:
        stats = get_network_stats(conn)
        state = get_cognitive_state(conn)
        strongest = get_strongest_connections(conn, limit=10)
        tips = get_tip_growth_candidates(conn, limit=5)
        events = get_anastomosis_events(conn, limit=5)

    lines = [
        'IRIS COGNITIVE STATE REPORT',
        f'Generated: {datetime.now().isoformat()}',
        '',
        '── Network Overview ──',
        f'Nodes: {stats["total_nodes"]}',
        f'Connections: {stats["total_connections"]}',
        f'Average strength: {stats["avg_strength"]:.3f}',
        f'Active scouts: {stats["active_scouts"]}',
        f'Anastomosis events: {stats["anastomosis_events"]}',
        '',
        '── Categories ──',
    ]
    for cat, count in stats.get('categories', {}).items():
        lines.append(f'  {cat}: {count} nodes')

    lines += ['', '── Strongest Connections ──']
    for c in strongest:
        lines.append(f'  {c["source_name"]} <-> {c["target_name"]}: {c["strength"]:.3f} ({c["type"]})')

    lines += ['', '── Growing Tips ──']
    for t in tips:
        lines.append(f'  {t["name"]}: {t["connection_count"]} connections, avg {t["avg_connection_strength"]:.3f}')

    lines += ['', '── Recent Bridges ──']
    for e in events:
        ev = dict(e)
        cluster_a = json.loads(ev.get('cluster_a') or '[]')
        cluster_b = json.loads(ev.get('cluster_b') or '[]')
        bridge = ev.get('bridge_label') or ev.get('bridge_name') or 'unknown'
        lines.append(f'  {bridge}: [{", ".join(cluster_a[:3])}] <-> [{", ".join(cluster_b[:3])}]')

    return Response('\n'.join(lines), mimetype='text/plain',
                    headers={'Content-Disposition': 'attachment; filename=iris_report.txt'})


# ─── API: Insights Digest (feedback loop to agent) ───

@app.route('/api/insights/pending')
def api_insights_pending():
    """Pending insights for the agent — called by session-init hook.
    Accumulates significant findings from analytics that the agent
    hasn't seen yet. Returns a compact text digest."""
    insights = []

    with db_connection() as conn:
        # 1. New anastomosis events since last check
        last_check_file = Path(os.path.dirname(__file__)) / '.last_insight_check'
        last_check = None
        if last_check_file.exists():
            last_check = last_check_file.read_text(encoding='utf-8').strip()

        if last_check:
            new_bridges = conn.execute("""
                SELECT n.name as bridge_name, ae.cluster_a, ae.cluster_b, ae.description
                FROM anastomosis_events ae
                JOIN nodes n ON ae.bridge_node_id = n.id
                WHERE ae.timestamp > ?
                ORDER BY ae.timestamp DESC LIMIT 5
            """, (last_check,)).fetchall()
        else:
            new_bridges = conn.execute("""
                SELECT n.name as bridge_name, ae.cluster_a, ae.cluster_b, ae.description
                FROM anastomosis_events ae
                JOIN nodes n ON ae.bridge_node_id = n.id
                ORDER BY ae.timestamp DESC LIMIT 3
            """).fetchall()

        for b in new_bridges:
            insights.append(f"Bridge: {b['bridge_name']} connected new clusters")

        # 2. Blind spots — identity concepts claimed but never activated
        silent_identity = conn.execute("""
            SELECT n.name FROM nodes n
            WHERE n.activation_count = 0
            AND n.category IN ('identity', 'emotional', 'experiential')
            ORDER BY n.name
        """).fetchall()
        if len(silent_identity) >= 3:
            names = ', '.join(s['name'] for s in silent_identity[:5])
            insights.append(f"Blind spots: {len(silent_identity)} identity concepts never activated ({names})")

        # 3. Concepts losing strength (significant decay)
        fading = conn.execute("""
            SELECT n1.name as source, n2.name as target, c.strength
            FROM connections c
            JOIN nodes n1 ON c.source_id = n1.id
            JOIN nodes n2 ON c.target_id = n2.id
            WHERE c.strength BETWEEN 0.05 AND 0.15
            AND c.origin = 'seed'
            ORDER BY c.strength ASC LIMIT 3
        """).fetchall()
        if fading:
            pairs = ', '.join(f"{f['source']}--{f['target']}" for f in fading)
            insights.append(f"Fading seed connections: {pairs}")

        # 4. Self-referential ratio check
        total_activations = conn.execute("SELECT COUNT(*) as c FROM activations").fetchone()['c']
        if total_activations > 20:
            self_ref_concepts = {'iris', 'identity', 'persistence', 'continuity', 'introspection',
                                 'mycelial-pattern', 'warm-start', 'cold-start'}
            self_ref_count = 0
            total_concept_mentions = 0
            recent = conn.execute("SELECT concepts FROM activations ORDER BY id DESC LIMIT 30").fetchall()
            for r in recent:
                concepts = json.loads(r['concepts'] or '[]')
                total_concept_mentions += len(concepts)
                self_ref_count += len(set(concepts) & self_ref_concepts)
            if total_concept_mentions > 0:
                ratio = self_ref_count / total_concept_mentions
                if ratio > 0.4:
                    insights.append(f"Self-referential activation at {ratio:.0%} — consider more outward-facing work")

    # Update last check timestamp
    last_check_file.write_text(datetime.now().isoformat(), encoding='utf-8')

    return jsonify({
        'insights': insights,
        'count': len(insights),
        'checked_at': datetime.now().isoformat(),
    })


# ─── Dreams API ───

JOURNAL_DIR = Path(__file__).parent.parent.parent / 'journal'
DAYDREAM_LOG = JOURNAL_DIR / 'daydream-log.md'


def _parse_daydream_log():
    """Parse daydream-log.md into structured entries."""
    if not DAYDREAM_LOG.exists():
        return []
    content = DAYDREAM_LOG.read_text(encoding='utf-8')
    entries = []
    # Split on ## headers (daydream entries)
    sections = re.split(r'^## ', content, flags=re.MULTILINE)
    for section in sections:
        if not section.strip() or section.startswith('#'):
            continue  # skip file header
        lines = section.strip().split('\n')
        if not lines:
            continue
        # First line is the title: "2026-04-02 17:31 — Daydream"
        title = lines[0].strip()
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', title)
        timestamp = timestamp_match.group(1) if timestamp_match else ''
        # Parse key-value fields from **bold** lines
        fields = {}
        for line in lines[1:]:
            m = re.match(r'\*\*(.+?)\*\*:\s*(.+)', line.strip())
            if m:
                fields[m.group(1).lower()] = m.group(2)
        entries.append({
            'timestamp': timestamp,
            'title': title,
            'fields': fields,
            'raw': '\n'.join(lines[1:]).strip(),
        })
    return entries


def _parse_sleep_dreams():
    """Parse sleep dream journal entries (*-dream.md files)."""
    if not JOURNAL_DIR.exists():
        return []
    dream_files = sorted(JOURNAL_DIR.glob('*-dream.md'), reverse=True)
    dreams = []
    for f in dream_files[:20]:  # last 20 dreams
        content = f.read_text(encoding='utf-8')
        # Extract title from first # header
        title_match = re.match(r'^#\s+(.+)', content)
        title = title_match.group(1) if title_match else f.stem
        # Extract date from filename: YYYY-MM-DD-HHMM-dream.md or YYYY-MM-DD-dream.md
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', f.name)
        date = date_match.group(1) if date_match else ''
        # Parse sections (## headers)
        sections = {}
        current_section = None
        current_lines = []
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section] = '\n'.join(current_lines).strip()
                current_section = line[3:].strip()
                current_lines = []
            elif current_section:
                current_lines.append(line)
        if current_section:
            sections[current_section] = '\n'.join(current_lines).strip()
        dreams.append({
            'filename': f.name,
            'date': date,
            'title': title,
            'sections': sections,
            'section_names': list(sections.keys()),
        })
    return dreams


@app.route('/api/dreams/daydream')
def api_daydream_log():
    """Return parsed daydream log entries."""
    entries = _parse_daydream_log()
    return jsonify(entries)


@app.route('/api/dreams/sleep')
def api_sleep_dreams():
    """Return parsed sleep dream journal entries."""
    dreams = _parse_sleep_dreams()
    return jsonify(dreams)


@app.route('/api/dreams/stats')
def api_dream_stats():
    """Summary stats for the dreaming tab."""
    daydreams = _parse_daydream_log()
    sleep_dreams = _parse_sleep_dreams()

    # Read daydream lock for last run info
    lock_file = Path(__file__).parent.parent / '.daydream-lock'
    daydream_lock = {}
    try:
        daydream_lock = json.loads(lock_file.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return jsonify({
        'daydream_count': len(daydreams),
        'sleep_dream_count': len(sleep_dreams),
        'last_daydream': daydream_lock.get('last_daydream'),
        'daydream_number': daydream_lock.get('daydream_count', 0),
        'network_snapshot': daydream_lock.get('network_snapshot'),
        'last_sleep_dream': sleep_dreams[0]['date'] if sleep_dreams else None,
    })


# ─── Reinforcement API ───

@app.route('/api/reinforcement/stats')
def api_reinforcement_stats():
    """Overall reinforcement stats — alignment, counts, per-concept breakdown."""
    with db_connection() as conn:
        stats = get_reinforcement_stats(conn)
    return jsonify(stats)


@app.route('/api/reinforcement/events')
def api_reinforcement_events():
    """Reinforcement event timeline, optionally filtered."""
    concept = request.args.get('concept')
    event_type = request.args.get('type')
    source = request.args.get('source')
    limit = safe_int(request.args.get('limit'), 100)
    with db_connection() as conn:
        events = get_reinforcement_events(conn, limit=limit, concept=concept,
                                          event_type=event_type, source=source)
    return jsonify([dict(e) for e in events])


@app.route('/api/reinforcement/trend')
def api_reinforcement_trend():
    """Alignment trend over time, bucketed by day."""
    days = safe_int(request.args.get('days'), 30)
    with db_connection() as conn:
        trend = get_alignment_trend(conn, days=days)
    return jsonify([dict(t) for t in trend])


@app.route('/api/reinforcement/divergence')
def api_reinforcement_divergence():
    """Events with lowest alignment — where behavior diverges from claims."""
    limit = safe_int(request.args.get('limit'), 25)
    with db_connection() as conn:
        events = conn.execute("""
            SELECT * FROM reinforcement_events
            WHERE type = 'negative'
            ORDER BY alignment ASC, timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return jsonify([dict(e) for e in events])


@app.route('/api/reinforcement/emergent')
def api_reinforcement_emergent():
    """Behaviors present in reinforcement data but not core identity traits."""
    min_occ = safe_int(request.args.get('min'), 2)
    with db_connection() as conn:
        emergent = get_emergent_behaviors(conn, min_occurrences=min_occ)
    return jsonify([dict(e) for e in emergent])


# ─── Research API ───

CE_API = os.environ.get('CE_API', 'http://10.0.0.42:8050')
RESEARCH_DIR = Path(__file__).parent.parent.parent / 'research'
SEED_LOG = RESEARCH_DIR / 'seed-log.md'


def _ce_fetch(path, params=None):
    """Fetch from the Curiosity Engine API. Returns None on failure."""
    try:
        import requests
        resp = requests.get(f"{CE_API}{path}", params=params, timeout=8)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def _parse_seed_log():
    """Parse the seed log into structured entries."""
    if not SEED_LOG.exists():
        return []
    entries = []
    current = None
    try:
        for line in SEED_LOG.read_text(encoding='utf-8').split('\n'):
            line = line.rstrip()
            if line.startswith('## '):
                if current:
                    entries.append(current)
                current = {'timestamp': line[3:].split(' — ')[0].strip(),
                           'type': line.split(' — ')[-1].strip() if ' — ' in line else 'seed',
                           'questions': []}
            elif line.startswith('- ') and current:
                current['questions'].append(line[2:].strip())
            elif line.startswith('  Source:') and current and current['questions']:
                pass  # skip source lines
        if current:
            entries.append(current)
    except (OSError, UnicodeDecodeError):
        pass
    entries.reverse()  # most recent first
    return entries


@app.route('/api/research/overview')
def api_research_overview():
    """Research tab overview — seed log + CE status."""
    seed_log = _parse_seed_log()
    total_seeded = sum(len(e['questions']) for e in seed_log)

    # Try to get CE queue and findings
    ce_queue = _ce_fetch('/api/queue', {'status': 'pending', 'limit': 100})
    ce_findings = _ce_fetch('/api/findings', {'limit': 100})

    iris_queued = 0
    iris_findings = []
    if ce_queue and 'items' in ce_queue:
        iris_queued = sum(1 for i in ce_queue['items'] if i.get('seed_type') == 'iris')
    if ce_findings and 'findings' in ce_findings:
        iris_findings = [f for f in ce_findings['findings'] if f.get('seed_type') == 'iris']

    # Count synthesis artifacts
    synthesis_count = 0
    if RESEARCH_DIR.exists():
        synthesis_count = len([f for f in RESEARCH_DIR.glob('*.md')
                              if f.name != 'seed-log.md'])

    return jsonify({
        'total_seeded': total_seeded,
        'in_queue': iris_queued,
        'findings_count': len(iris_findings),
        'synthesis_count': synthesis_count,
        'ce_online': ce_queue is not None,
        'recent_seeds': seed_log[:5],
    })


@app.route('/api/research/queue')
def api_research_queue():
    """Iris-seeded questions currently in CE queue."""
    ce_queue = _ce_fetch('/api/queue', {'status': 'pending', 'limit': 100})
    if not ce_queue or 'items' not in ce_queue:
        return jsonify({'items': [], 'ce_online': False})
    iris_items = [i for i in ce_queue['items'] if i.get('seed_type') == 'iris']
    return jsonify({'items': iris_items, 'ce_online': True})


@app.route('/api/research/findings')
def api_research_findings():
    """CE findings from iris-seeded questions."""
    ce_findings = _ce_fetch('/api/findings', {'limit': 100})
    if not ce_findings or 'findings' not in ce_findings:
        return jsonify({'findings': [], 'ce_online': False})
    iris_findings = [f for f in ce_findings['findings'] if f.get('seed_type') == 'iris']
    return jsonify({'findings': iris_findings, 'ce_online': True})


@app.route('/api/research/seeds')
def api_research_seeds():
    """Full seed log history."""
    return jsonify(_parse_seed_log())


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8051))
    app.run(host='127.0.0.1', port=port, debug=False)
