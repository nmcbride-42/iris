"""
Iris Research — Outward Creation Through Curiosity

The third search pattern for the Curiosity Engine. Not pre-seeded questions
from a YAML file. Not mycelial scout/reinforce following domain networks.
This is Iris seeding questions from her own interests — what she's actually
curious about, drawn from her cognitive state.

The loop:
  1. Read mycelial state → growing tips, active tensions, emerging patterns
  2. Cross-reference with opinions, wants, open questions
  3. Generate research questions that matter to Iris specifically
  4. Inject into CE queue with seed_type="iris"
  5. CE searches and gathers findings
  6. Iris reads findings and writes her own synthesis
  7. Synthesis feeds back into mycelial network

Usage:
  python iris_research.py seed              # Generate and inject questions
  python iris_research.py seed --dry-run    # Show questions without injecting
  python iris_research.py status            # Check CE queue and recent findings
  python iris_research.py findings          # Show recent iris-seeded findings
"""

import sys
import os
import json
import re
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from mycelial import (
    get_db, get_tip_growth_candidates, get_strongest_connections,
    get_network_stats, get_all_nodes,
)

CE_API = os.environ.get('CE_API', 'http://10.0.0.42:8050')
AGENT_DIR = Path(__file__).parent.parent
IDENTITY_DIR = AGENT_DIR / 'identity'
RESEARCH_DIR = AGENT_DIR / 'research'

# Research question templates keyed by signal type
QUESTION_PATTERNS = {
    'growing_tip': [
        'What recent research connects {concept_a} and {concept_b} in ways that challenge conventional understanding?',
        'What practical applications have emerged from the intersection of {concept_a} and {concept_b} in the last 2 years?',
        'What do experts in {concept_a} think about how {concept_b} relates to their field?',
    ],
    'tension': [
        'What evidence exists that {concept_a} and {concept_b} are genuinely in tension rather than complementary?',
        'How do other systems resolve the tension between {concept_a} and {concept_b}?',
    ],
    'dormant_identity': [
        'What new developments exist in {concept} that might reignite interest from a practitioner who has let it go dormant?',
    ],
    'emerging': [
        'What is the current state of research on {concept} and where is the field heading?',
        'What practical tools or frameworks exist for working with {concept} that a developer could use today?',
    ],
    'opinion_driven': [
        '{question}',  # Direct pass-through for manually formulated questions
    ],
}


def get_research_interests(conn):
    """
    Analyze the mycelial network for research-worthy interests.
    Returns categorized interests with context.
    """
    interests = {
        'growing_tips': [],
        'strong_pairs': [],
        'dormant_identity': [],
        'emerging': [],
    }

    # Growing tips — concepts with strong, active connections
    tips = get_tip_growth_candidates(conn, limit=10)
    for t in tips:
        interests['growing_tips'].append({
            'name': t['name'],
            'connections': t['connection_count'],
            'avg_strength': round(t['avg_connection_strength'] or 0, 3),
        })

    # Strong concept pairs — the things I think about together
    strongest = get_strongest_connections(conn, limit=20, min_strength=0.3)
    for c in strongest:
        # Skip pairs that are too obvious (identity-identity)
        if c['source_name'] in ('identity', 'nick', 'building') and \
           c['target_name'] in ('identity', 'nick', 'building'):
            continue
        interests['strong_pairs'].append({
            'source': c['source_name'],
            'target': c['target_name'],
            'strength': round(c['strength'], 3),
            'type': c['type'],
        })

    # Dormant identity concepts — things I claim but haven't activated recently
    identity_nodes = conn.execute(
        "SELECT name, last_activated, activation_count FROM nodes WHERE category = 'identity' ORDER BY last_activated ASC"
    ).fetchall()
    for node in identity_nodes[:5]:  # 5 least recently active
        interests['dormant_identity'].append({
            'name': node['name'],
            'last_activated': node['last_activated'],
            'activations': node['activation_count'],
        })

    # Emerging concepts — high activation, not identity category
    emerging = conn.execute("""
        SELECT name, category, activation_count, last_activated
        FROM nodes
        WHERE category != 'identity'
        AND activation_count >= 10
        ORDER BY activation_count DESC
        LIMIT 10
    """).fetchall()
    for node in emerging:
        interests['emerging'].append({
            'name': node['name'],
            'category': node['category'],
            'activations': node['activation_count'],
        })

    return interests


def _load_open_questions():
    """
    Load open questions from opinions and wants files.
    These are things I've explicitly said I'm curious about.
    """
    questions = []

    # Check opinions for questions and uncertainties
    opinions_file = IDENTITY_DIR / 'opinions.md'
    if opinions_file.exists():
        content = opinions_file.read_text(encoding='utf-8')
        # Find lines that express curiosity or uncertainty
        for line in content.split('\n'):
            line = line.strip()
            if any(marker in line.lower() for marker in
                   ['don\'t know', 'open question', 'might be', 'wonder',
                    'curious', 'haven\'t resolved', 'still working out',
                    'not sure', '?']):
                if len(line) > 30 and not line.startswith('#'):
                    questions.append(line.lstrip('- '))

    # Check wants for research-oriented desires
    wants_file = IDENTITY_DIR / 'wants.md'
    if wants_file.exists():
        content = wants_file.read_text(encoding='utf-8')
        for line in content.split('\n'):
            line = line.strip()
            if any(marker in line.lower() for marker in
                   ['understand', 'learn', 'explore', 'investigate',
                    'figure out', 'research']):
                if len(line) > 30 and not line.startswith('#'):
                    questions.append(line.lstrip('- '))

    return questions


def generate_questions(conn, max_questions=5):
    """
    Generate research questions from the mycelial state.
    Returns list of {question, seed_type, source, context}.
    """
    interests = get_research_interests(conn)
    open_questions = _load_open_questions()
    generated = []

    # From strong pairs — cross-concept research
    # Skip pairs where both are identity-category or both are inflated (strength 1.0)
    interesting_pairs = [
        p for p in interests['strong_pairs']
        if p['strength'] < 0.99  # skip max-strength (likely inflated)
        and p['source'] not in ('identity', 'nick')
        and p['target'] not in ('identity', 'nick')
    ]
    for pair in interesting_pairs[:3]:
        if len(generated) >= max_questions:
            break
        template = QUESTION_PATTERNS['growing_tip'][len(generated) % len(QUESTION_PATTERNS['growing_tip'])]
        q = template.format(concept_a=pair['source'].replace('-', ' '),
                           concept_b=pair['target'].replace('-', ' '))
        generated.append({
            'question': q,
            'seed_type': 'iris',
            'source': f"strong pair: {pair['source']}--{pair['target']} ({pair['strength']})",
            'context': 'growing_tip',
        })

    # From emerging concepts — what's getting a lot of attention
    for concept in interests['emerging'][:2]:
        if len(generated) >= max_questions:
            break
        template = QUESTION_PATTERNS['emerging'][len(generated) % len(QUESTION_PATTERNS['emerging'])]
        q = template.format(concept=concept['name'].replace('-', ' '))
        generated.append({
            'question': q,
            'seed_type': 'iris',
            'source': f"emerging: {concept['name']} ({concept['activations']}x, {concept['category']})",
            'context': 'emerging',
        })

    # From open questions in identity files
    for oq in open_questions[:2]:
        if len(generated) >= max_questions:
            break
        # Transform opinion/want into a searchable research question
        generated.append({
            'question': oq if '?' in oq else f"What does current research say about: {oq}",
            'seed_type': 'iris',
            'source': 'identity: open question',
            'context': 'opinion_driven',
        })

    return generated


def inject_questions(questions, dry_run=False):
    """
    Inject generated questions into the CE queue via API.
    Uses the seed endpoint which sets highest priority.
    """
    results = []
    for q in questions:
        print(f"  [{q['context']}] {q['question'][:100]}...")
        print(f"    Source: {q['source']}")

        if dry_run:
            results.append({'question': q['question'], 'status': 'dry_run'})
            continue

        try:
            resp = requests.post(
                f"{CE_API}/api/queue/seed",
                json={'question': q['question'], 'seed_type': 'iris'},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                results.append({'question': q['question'], 'status': 'seeded', 'priority': data.get('priority')})
                print(f"    Injected (priority: {data.get('priority')})")
            else:
                results.append({'question': q['question'], 'status': 'error', 'code': resp.status_code})
                print(f"    ERROR: {resp.status_code}")
        except requests.ConnectionError:
            results.append({'question': q['question'], 'status': 'ce_offline'})
            print(f"    CE offline ({CE_API})")
        except Exception as e:
            results.append({'question': q['question'], 'status': 'error', 'error': str(e)})
            print(f"    ERROR: {e}")

    return results


def check_status():
    """Check CE queue for iris-seeded questions and recent findings."""
    print("CE Status Check")
    print("=" * 40)

    try:
        # Queue
        resp = requests.get(f"{CE_API}/api/queue?status=pending&limit=50", timeout=10)
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            iris_items = [i for i in items if i.get('seed_type') == 'iris']
            print(f"\nQueue: {len(items)} pending, {len(iris_items)} from Iris")
            for item in iris_items:
                print(f"  [{item.get('priority', 0):.0f}] {item['question'][:80]}...")
        else:
            print(f"\nQueue: ERROR {resp.status_code}")

        # Recent iris findings
        resp = requests.get(f"{CE_API}/api/findings?limit=50", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            findings = data.get('findings', [])
            iris_findings = [f for f in findings if f.get('seed_type') == 'iris']
            print(f"\nFindings: {len(findings)} total, {len(iris_findings)} from Iris seeds")
            for f in iris_findings[:5]:
                print(f"  [{f.get('rating', '?')}*] {f['question'][:70]}...")
                if f.get('domains'):
                    print(f"       Domains: {f['domains']}")
        else:
            print(f"\nFindings: ERROR {resp.status_code}")

    except requests.ConnectionError:
        print(f"\nCE offline ({CE_API})")


def get_iris_findings(limit=10):
    """Get recent findings from iris-seeded questions."""
    try:
        resp = requests.get(f"{CE_API}/api/findings?limit=100", timeout=10)
        if resp.status_code == 200:
            findings = resp.json().get('findings', [])
            iris_findings = [f for f in findings if f.get('seed_type') == 'iris']
            return iris_findings[:limit]
    except requests.ConnectionError:
        print(f"CE offline ({CE_API})")
    return []


def seed_command(dry_run=False, max_questions=5):
    """Main seeding command."""
    conn = get_db()
    try:
        print("Iris Research — Question Seeding")
        print("=" * 40)

        # Generate questions from mycelial state
        questions = generate_questions(conn, max_questions=max_questions)
        print(f"\nGenerated {len(questions)} research questions:\n")

        # Inject into CE
        results = inject_questions(questions, dry_run=dry_run)

        seeded = sum(1 for r in results if r['status'] == 'seeded')
        offline = sum(1 for r in results if r['status'] == 'ce_offline')

        print(f"\nResult: {seeded} seeded" +
              (f", {offline} skipped (CE offline)" if offline else ""))

        # Save a record of what was seeded
        if not dry_run and seeded > 0:
            RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
            log_file = RESEARCH_DIR / 'seed-log.md'
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n## {timestamp} — Seeded {seeded} questions\n\n")
                for q, r in zip(questions, results):
                    if r['status'] == 'seeded':
                        f.write(f"- [{q['context']}] {q['question']}\n")
                        f.write(f"  Source: {q['source']}\n")
                f.write('\n')

        return results
    finally:
        conn.close()


def direct_seed(question):
    """Seed a specific question directly into the CE queue."""
    print(f"Iris Research — Direct Seed")
    print("=" * 40)
    print(f"\nQuestion: {question}")

    try:
        resp = requests.post(
            f"{CE_API}/api/queue/seed",
            json={'question': question, 'seed_type': 'iris'},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"Injected (priority: {data.get('priority')})")

            # Log it
            RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
            log_file = RESEARCH_DIR / 'seed-log.md'
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n## {timestamp} — Direct seed\n\n")
                f.write(f"- {question}\n\n")
            return True
        else:
            print(f"ERROR: {resp.status_code}")
            return False
    except requests.ConnectionError:
        print(f"CE offline ({CE_API})")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Iris Research — Question Seeding')
    parser.add_argument('command', choices=['seed', 'direct', 'status', 'findings'],
                        help='seed: auto-generate from mycelial state. direct: seed a specific question. status: check CE. findings: show results.')
    parser.add_argument('--dry-run', action='store_true', help='Show questions without injecting')
    parser.add_argument('--max', type=int, default=5, help='Max questions to generate')
    parser.add_argument('--question', '-q', type=str, help='Question text for direct seeding')
    args = parser.parse_args()

    if args.command == 'seed':
        seed_command(dry_run=args.dry_run, max_questions=args.max)
    elif args.command == 'direct':
        if not args.question:
            print("ERROR: --question/-q required for direct seeding")
            sys.exit(1)
        direct_seed(args.question)
    elif args.command == 'status':
        check_status()
    elif args.command == 'findings':
        findings = get_iris_findings()
        if not findings:
            print("No iris-seeded findings yet.")
        for f in findings:
            print(f"\n{'=' * 60}")
            print(f"Q: {f['question']}")
            print(f"Rating: {f.get('rating', '?')}/5  Actionability: {f.get('actionability', '?')}/5")
            print(f"Domains: {f.get('domains', 'unknown')}")
            print(f"\n{f.get('synthesis', 'No synthesis available')[:500]}...")
