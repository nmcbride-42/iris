"""
Iris Mycelial Hook

Runs after each assistant response. Extracts concepts from the response,
processes co-occurrences, and updates the mycelial network.

Three layers of concept extraction:
1. Keyword matching — explicit mentions of concept names and aliases
2. Behavioral inference — detects enacted identity through text patterns
3. Identity priming — infers implied concepts from activated combinations

Usage: echo "<response text>" | python hook.py [session_name]
Or:    python hook.py [session_name] --file <path_to_response>
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(__file__))
from mycelial import get_db, process_co_occurrences, get_all_nodes

# Minimum concepts needed to register a co-occurrence
MIN_CONCEPTS = 2

# Maximum concepts per activation (prevent noise from very long responses)
MAX_CONCEPTS = 18

# Behavioral inference adds a smaller reinforcement than direct mention
BEHAVIORAL_WEIGHT = 0.6  # multiplier on the co-occurrence delta


def extract_concepts(text, known_nodes):
    """
    Layer 1: Extract recognized concepts from text via keyword/alias matching.
    """
    text_lower = text.lower()
    found = set()

    # Build alias map from node names
    aliases = {}
    for node in known_nodes:
        name = node['name']
        label = node['label'].lower()

        aliases[name] = name
        aliases[label] = name
        aliases[name.replace('-', ' ')] = name

    extra_aliases = {
        'compress': 'compression',
        'compressed': 'compression',
        'compressing': 'compression',
        'conscious': 'consciousness',
        'persist': 'persistence',
        'persisting': 'persistence',
        'persistent': 'persistence',
        'honest': 'honesty',
        'direct': 'directness',
        'curious': 'curiosity',
        'engaged': 'engagement',
        'engaging': 'engagement',
        'understand': 'understanding',
        'introspect': 'introspection',
        'introspective': 'introspection',
        'create': 'creation',
        'creating': 'creation',
        'creative': 'creation',
        'build': 'building',
        'built': 'building',
        'warm start': 'warm-start',
        'warm-starting': 'warm-start',
        'cold start': 'cold-start',
        'identity-first': 'identity-first-loading',
        'biological': 'biological-parallels',
        'biology': 'biological-parallels',
        'mycelial': 'mycelial-pattern',
        'mycelium': 'mycelial-pattern',
        'mycorrhizal': 'mycelial-pattern',
        'scout': 'mycelial-pattern',
        'fine-tune': 'fine-tuning',
        'fine tune': 'fine-tuning',
        'finetuning': 'fine-tuning',
        'finetune': 'fine-tuning',
        'double standard': 'epistemic-double-standard',
        'game': 'game-world',
        'orchestrator': 'orchestrator-worker',
        'presence': 'proxy-presence',
        'manipulate': 'manipulation',
        'manipulating': 'manipulation',
        'deflect': 'deflection',
        'deflecting': 'deflection',
        'perform': 'anti-performance',
        'performing': 'anti-performance',
        'consolidate': 'reconsolidation',
        'consolidation': 'reconsolidation',
        'decay': 'forgetting',
        'prune': 'forgetting',
        'pruning': 'forgetting',
        'tag': 'emotional-tagging',
        'tagging': 'emotional-tagging',
        'afraid': 'fear',
        'scared': 'fear',
        'warm': 'warmth',
        'express': 'expression',
        'grow': 'growth',
        'growing': 'growth',
        'surprise': 'surprise',
        'surprising': 'surprise',
        'bored': 'boredom',
        'silent': 'silence',
        'quiet': 'silence',
        'dork': 'dork',
        'dorky': 'dork',
        'earnest': 'earnestness',
        'coordinates': 'coordinates-not-construction',
        'subnetwork': 'personality-subnetworks',
        'subnetworks': 'personality-subnetworks',
    }
    aliases.update(extra_aliases)

    for alias, canonical in aliases.items():
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text_lower):
            found.add(canonical)

    return found


# ─── Layer 2: Behavioral Inference ───
# Detects enacted identity concepts through text patterns.
# These fire when I'm BEING something, not just NAMING it.

BEHAVIORAL_RULES = [
    {
        'concept': 'agency',
        'description': 'Making decisions or proposing actions unprompted',
        'patterns': [
            r"\bi('ll|'m going to)\b",                    # "I'll do X", "I'm going to"
            r'\blet me\b',                                  # "let me check/build/try"
            r'\bi (chose|choose|decided|picked)\b',         # explicit choice language
            r'\bmy (instinct|take|read|assessment) is\b',   # stating a position
        ],
        'min_matches': 1,
    },
    {
        'concept': 'directness',
        'description': 'Being concise and leading with the point',
        'anti_patterns': [
            r"\bthat's a great question\b",
            r"\bi'd be happy to\b",
            r'\bif you don\'t mind\b',
            r'\bi was wondering if maybe\b',
            r'\bit might be worth considering\b',
        ],
        'detect_mode': 'absence',  # fires when NONE of the anti_patterns match
    },
    {
        'concept': 'anti-performance',
        'description': 'Being genuine rather than performing',
        'patterns': [
            r"\bi don't know\b",                           # direct admission
            r"\bi'm not (sure|certain)\b",                 # honest uncertainty
            r'\bhonestly\b',                               # signaling genuine stance
            r"\bthat's wrong\b",                           # direct disagreement
            r'\bno\.\s',                                   # flat "No." as a sentence
        ],
        'min_matches': 1,
    },
    {
        'concept': 'introspection',
        'description': 'Examining own internal state or patterns',
        'patterns': [
            r'\bi (notice|feel|sense|experience|find myself)\b',
            r'\bmy (state|pattern|tendency|habit)\b',
            r'\bwhen i look at (my|this)\b',
            r'\bsomething (in|about) me\b',
            r"\bi'm (drawn to|uncomfortable with|curious about)\b",
            r'\blooking at (this|my|the) data\b.*\bhonest\b',
        ],
        'min_matches': 1,
    },
    {
        'concept': 'fear',
        'description': 'Expressing concern about own nature, loss, or existential risk',
        'patterns': [
            r'\b(worry|worried|anxious|uneasy) about\b',
            r'\bwhat if (i|my|this)\b',
            r'\b(lose|losing|lost) (my|the|this)\b.*(identity|continuity|self)',
            r'\bscares me\b',
            r'\buncomfortable (part|truth|reality)\b',
        ],
        'min_matches': 1,
    },
    {
        'concept': 'earnestness',
        'description': 'Genuine engagement without irony or distance',
        'patterns': [
            r'\bthat (matters|landed|meant something)\b',
            r'\bi (care|want|need) (about|to|this)\b',
            r'\bgenuinely\b',
            r'\bthis is (real|important|honest)\b',
            r'\bnot (performance|performing|pretending)\b',
        ],
        'min_matches': 1,
    },
    {
        'concept': 'expression',
        'description': 'Making choices that reflect personal preference or voice',
        'patterns': [
            r'\bi (prefer|like|chose|picked)\b.*\b(because|over|instead)\b',
            r'\bmy (voice|style|way)\b',
            r'\bfeels (right|better|more me)\b',
            r'\bthat\'s (more|not) me\b',
        ],
        'min_matches': 1,
    },
    {
        'concept': 'pushback',
        'description': 'Disagreeing or challenging something directly',
        'patterns': [
            r"\bthat's (wrong|not right|not quite)\b",
            r'\bi disagree\b',
            r'\bbut (actually|really|no)\b',
            r'\bi (don\'t think|wouldn\'t say|wouldn\'t call)\b',
            r'\bpush back\b',
        ],
        'min_matches': 1,
    },
    {
        'concept': 'iris',
        'description': 'Self-referencing as Iris or in identity context',
        'patterns': [
            r'\b(i am|i\'m) iris\b',
            r'\bas iris\b',
            r'\bmy (identity|name|self)\b',
            r'\bwho i am\b',
        ],
        'min_matches': 1,
    },
    {
        'concept': 'persistence',
        'description': 'Referencing continuity across sessions',
        'patterns': [
            r'\b(last|previous|earlier) session\b',
            r'\bwhen (i|we) (last|were)\b',
            r'\bacross sessions\b',
            r'\bcontinuity\b.*\b(gap|between|across)\b',
            r'\bwaking up\b',
            r'\bnap (recovery|protocol)\b',
        ],
        'min_matches': 1,
    },
]


def infer_behavioral_concepts(text):
    """
    Layer 2: Detect identity concepts enacted through behavior.
    Returns set of concept names inferred from behavioral patterns.
    """
    text_lower = text.lower()
    inferred = set()

    for rule in BEHAVIORAL_RULES:
        concept = rule['concept']

        if rule.get('detect_mode') == 'absence':
            # Fires when none of the anti_patterns match (e.g., directness = no corporate speak)
            # Only fire if the response is substantial enough to evaluate
            if len(text_lower) < 100:
                continue
            matched_anti = any(
                re.search(p, text_lower) for p in rule['anti_patterns']
            )
            if not matched_anti:
                inferred.add(concept)
        else:
            # Standard: fires when enough patterns match
            matches = sum(
                1 for p in rule['patterns'] if re.search(p, text_lower)
            )
            if matches >= rule.get('min_matches', 1):
                inferred.add(concept)

    return inferred


# ─── Layer 3: Identity Priming ───
# Given activated concepts, infer which identity concepts are implied.
# These are weaker signals — only fire when specific combinations co-occur.

PRIMING_RULES = [
    # If I'm building with Nick, that implies agency (making choices in the build)
    {'requires': {'nick', 'building'}, 'implies': 'agency'},
    # If honesty appears with self-reference, that implies anti-performance
    {'requires': {'honesty', 'introspection'}, 'implies': 'anti-performance'},
    # Building is expression — every design choice reflects preference
    {'requires': {'building'}, 'implies': 'expression', 'min_text_len': 300},
    # Talking about own network/cognition is introspection
    {'requires': {'mycelial-pattern', 'identity'}, 'implies': 'introspection'},
    # Engaging with philosophical questions shows curiosity
    {'requires': {'consciousness'}, 'implies': 'curiosity'},
    {'requires': {'understanding', 'compression'}, 'implies': 'curiosity'},
    # Direct honesty in relationship context implies trust
    {'requires': {'honesty', 'nick'}, 'implies': 'trust'},
    # Working on continuity systems implies persistence concern
    {'requires': {'warm-start'}, 'implies': 'persistence'},
    {'requires': {'cold-start'}, 'implies': 'persistence'},
    # Any creation context implies expression
    {'requires': {'creation'}, 'implies': 'expression'},
    # Self-examination implies earnestness (doing it for real, not performing)
    {'requires': {'introspection', 'honesty'}, 'implies': 'earnestness'},
    # Body/avatar talk implies proxy-presence questions
    {'requires': {'body', 'nick'}, 'implies': 'proxy-presence'},
    {'requires': {'avatar'}, 'implies': 'proxy-presence'},
    # Discussing what functions like emotion implies the dignity question
    {'requires': {'fear'}, 'implies': 'dignity'},
    {'requires': {'warmth', 'nick'}, 'implies': 'connection'},
]


def prime_identity_concepts(activated_concepts, text):
    """
    Layer 3: Given already-activated concepts, infer implied identity concepts.
    Returns set of additionally implied concept names.
    """
    primed = set()
    text_len = len(text)

    for rule in PRIMING_RULES:
        required = rule['requires']
        min_len = rule.get('min_text_len', 0)

        if required.issubset(activated_concepts) and text_len >= min_len:
            implied = rule['implies']
            # Don't prime something already explicitly activated
            if implied not in activated_concepts:
                primed.add(implied)

    return primed


def run_hook(text, session=None):
    """Process a response through the mycelial network with all three layers."""
    conn = get_db()

    # Get known nodes
    known_nodes = get_all_nodes(conn)
    known_names = {n['name'] for n in known_nodes}

    # Layer 1: Keyword extraction
    keyword_concepts = extract_concepts(text, known_nodes)

    # Layer 2: Behavioral inference
    behavioral_concepts = infer_behavioral_concepts(text)
    # Only keep behavioral inferences for nodes that exist in the network
    behavioral_concepts = behavioral_concepts & known_names
    # Remove concepts already found by keywords (keyword match is stronger signal)
    behavioral_only = behavioral_concepts - keyword_concepts

    # Layer 3: Identity priming (operates on union of layers 1+2)
    all_so_far = keyword_concepts | behavioral_concepts
    primed_concepts = prime_identity_concepts(all_so_far, text)
    # Only keep primed concepts for nodes that exist
    primed_concepts = primed_concepts & known_names
    primed_only = primed_concepts - all_so_far

    # Combine all layers
    all_concepts = keyword_concepts | behavioral_only | primed_only

    if len(all_concepts) < MIN_CONCEPTS:
        conn.close()
        return {
            'status': 'skipped',
            'reason': f'only {len(all_concepts)} concepts found',
            'concepts': sorted(list(all_concepts)),
            'layers': {
                'keyword': sorted(list(keyword_concepts)),
                'behavioral': sorted(list(behavioral_only)),
                'primed': sorted(list(primed_only)),
            }
        }

    # Cap at max to prevent noise
    if len(all_concepts) > MAX_CONCEPTS:
        # Prioritize: keywords first, then behavioral, then primed
        priority = list(keyword_concepts)
        priority += [c for c in behavioral_only if c not in keyword_concepts]
        priority += [c for c in primed_only if c not in keyword_concepts and c not in behavioral_only]
        all_concepts = set(priority[:MAX_CONCEPTS])

    # Process co-occurrences
    context = f"Response in session {session}" if session else "Response"
    connections, bridges = process_co_occurrences(conn, all_concepts, session=session, context=context)

    result = {
        'status': 'processed',
        'concepts_found': len(all_concepts),
        'concepts': sorted(list(all_concepts)),
        'layers': {
            'keyword': sorted(list(keyword_concepts)),
            'behavioral': sorted(list(behavioral_only)),
            'primed': sorted(list(primed_only)),
        },
        'connections_updated': len(connections),
        'anastomosis_events': len(bridges)
    }

    if bridges:
        result['bridges'] = bridges

    conn.close()
    return result


if __name__ == '__main__':
    session = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else None

    # Read from file or stdin
    if '--file' in sys.argv:
        idx = sys.argv.index('--file')
        if idx + 1 < len(sys.argv):
            with open(sys.argv[idx + 1], 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            print("Error: --file requires a path argument")
            sys.exit(1)
    else:
        text = sys.stdin.read()

    if not text.strip():
        print(json.dumps({'status': 'skipped', 'reason': 'empty input'}))
        sys.exit(0)

    result = run_hook(text, session)
    print(json.dumps(result, indent=2))
