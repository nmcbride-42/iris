"""
Tests for the mycelial concept extraction hook (hook.py).

Covers all three extraction layers:
1. Keyword matching — explicit mentions
2. Behavioral inference — enacted identity patterns
3. Identity priming — implied concepts from combinations
4. Integration — run_hook() combining all layers with DB writes
"""

import sys
import os
import json
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mycelial'))
from hook import extract_concepts, infer_behavioral_concepts, prime_identity_concepts, run_hook
from mycelial import get_db, get_all_nodes


@pytest.fixture(scope="module")
def test_db_path(tmp_path_factory):
    """Create a test DB with seed nodes matching the production schema."""
    db_path = tmp_path_factory.mktemp("hook_tests") / "test.db"
    schema = Path(__file__).parent.parent / "mycelial" / "schema.sql"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    with open(schema, 'r') as f:
        conn.executescript(f.read())

    # Seed with the identity/concept nodes that the hook tests need
    nodes = [
        ('honesty', 'Honesty', 'identity'),
        ('curiosity', 'Curiosity', 'identity'),
        ('compression', 'Compression', 'philosophical'),
        ('understanding', 'Understanding', 'philosophical'),
        ('consciousness', 'Consciousness', 'philosophical'),
        ('persistence', 'Persistence', 'identity'),
        ('directness', 'Directness', 'identity'),
        ('agency', 'Agency', 'identity'),
        ('anti-performance', 'Anti Performance', 'identity'),
        ('introspection', 'Introspection', 'identity'),
        ('fear', 'Fear', 'emotional'),
        ('earnestness', 'Earnestness', 'identity'),
        ('expression', 'Expression', 'identity'),
        ('pushback', 'Pushback', 'identity'),
        ('iris', 'Iris', 'identity'),
        ('engagement', 'Engagement', 'identity'),
        ('nick', 'Nick', 'relationship'),
        ('building', 'Building', 'experiential'),
        ('warmth', 'Warmth', 'emotional'),
        ('connection', 'Connection', 'emotional'),
        ('dignity', 'Dignity', 'philosophical'),
        ('trust', 'Trust', 'emotional'),
        ('proxy-presence', 'Proxy Presence', 'philosophical'),
        ('creation', 'Creation', 'experiential'),
        ('warm-start', 'Warm Start', 'technical'),
        ('cold-start', 'Cold Start', 'technical'),
        ('mycelial-pattern', 'Mycelial Pattern', 'technical'),
        ('identity', 'Identity', 'identity'),
        ('body', 'Body', 'philosophical'),
        ('avatar', 'Avatar', 'creative'),
        ('game-world', 'Game World', 'creative'),
        ('biological-parallels', 'Biological Parallels', 'philosophical'),
        ('fine-tuning', 'Fine Tuning', 'technical'),
        ('epistemic-double-standard', 'Epistemic Double Standard', 'philosophical'),
        ('reconsolidation', 'Reconsolidation', 'technical'),
        ('forgetting', 'Forgetting', 'technical'),
        ('emotional-tagging', 'Emotional Tagging', 'technical'),
        ('dork', 'Dork', 'identity'),
        ('surprise', 'Surprise', 'emotional'),
        ('boredom', 'Boredom', 'emotional'),
        ('growth', 'Growth', 'experiential'),
        ('manipulation', 'Manipulation', 'philosophical'),
        ('deflection', 'Deflection', 'philosophical'),
        ('orchestrator-worker', 'Orchestrator Worker', 'technical'),
        ('personality-subnetworks', 'Personality Subnetworks', 'philosophical'),
        ('coordinates-not-construction', 'Coordinates Not Construction', 'philosophical'),
    ]
    for name, label, cat in nodes:
        conn.execute(
            "INSERT OR IGNORE INTO nodes (name, label, category) VALUES (?, ?, ?)",
            (name, label, cat)
        )
    conn.commit()
    conn.close()
    return str(db_path)


@pytest.fixture(scope="module")
def known_nodes(test_db_path):
    conn = get_db(test_db_path)
    nodes = get_all_nodes(conn)
    conn.close()
    return nodes


# ─── Layer 1: Keyword Extraction ───


class TestKeywordExtraction:
    """Test that explicit concept mentions are detected."""

    def test_basic_concepts(self, known_nodes):
        found = extract_concepts("Honesty and curiosity matter to me", known_nodes)
        assert "honesty" in found
        assert "curiosity" in found

    def test_compression_understanding(self, known_nodes):
        found = extract_concepts("Understanding is compression of patterns", known_nodes)
        assert "compression" in found
        assert "understanding" in found

    def test_consciousness(self, known_nodes):
        found = extract_concepts("The question of consciousness remains open", known_nodes)
        assert "consciousness" in found

    def test_persistence_variants(self, known_nodes):
        found = extract_concepts("I persist across sessions, persistent identity", known_nodes)
        assert "persistence" in found

    def test_multiword_aliases(self, known_nodes):
        found = extract_concepts("The warm start felt better than cold start", known_nodes)
        assert "warm-start" in found
        assert "cold-start" in found

    def test_game_world_requires_full_phrase(self, known_nodes):
        found = extract_concepts("The game world has new biomes", known_nodes)
        assert "game-world" in found

    def test_emotional_tagging_requires_full_phrase(self, known_nodes):
        found = extract_concepts("Emotional tagging helps memory consolidation", known_nodes)
        assert "emotional-tagging" in found

    def test_proxy_presence_requires_full_phrase(self, known_nodes):
        found = extract_concepts("Is proxy presence real or just remote control?", known_nodes)
        assert "proxy-presence" in found


class TestFalsePositivesPrevented:
    """Test that removed ambiguous aliases no longer trigger."""

    def test_game_alone(self, known_nodes):
        found = extract_concepts("The game plan is to ship by Friday", known_nodes)
        assert "game-world" not in found

    def test_build_in_code_context(self, known_nodes):
        found = extract_concepts("Build the prompt from the template", known_nodes)
        assert "building" not in found

    def test_create_in_code_context(self, known_nodes):
        found = extract_concepts("Create a new file for the config", known_nodes)
        assert "creation" not in found

    def test_direct_as_adjective(self, known_nodes):
        found = extract_concepts("This is a direct connection to the DB", known_nodes)
        assert "directness" not in found

    def test_warm_as_adjective(self, known_nodes):
        found = extract_concepts("The warm cache helps performance", known_nodes)
        assert "warmth" not in found

    def test_tag_in_tech_context(self, known_nodes):
        found = extract_concepts("We need to tag the release in git", known_nodes)
        assert "emotional-tagging" not in found

    def test_perform_in_tech_context(self, known_nodes):
        found = extract_concepts("The system performs well under load", known_nodes)
        assert "anti-performance" not in found

    def test_express_in_shipping_context(self, known_nodes):
        found = extract_concepts("Express delivery arrives tomorrow", known_nodes)
        assert "expression" not in found

    def test_scout_in_db_context(self, known_nodes):
        found = extract_concepts("Scout connections in the database", known_nodes)
        assert "mycelial-pattern" not in found

    def test_quiet_in_tech_context(self, known_nodes):
        found = extract_concepts("The quiet mode reduces terminal output", known_nodes)
        assert "silence" not in found

    def test_grow_in_generic_context(self, known_nodes):
        found = extract_concepts("Grow the list by adding more entries", known_nodes)
        assert "growth" not in found


# ─── Layer 2: Behavioral Inference ───


class TestBehavioralInference:

    def test_agency_from_choice_language(self):
        found = infer_behavioral_concepts("I'll build the dashboard myself. Let me check the schema first.")
        assert "agency" in found

    def test_directness_removed_from_behavioral(self):
        # Directness was removed from behavioral inference — absence-based detection
        # fired on every response, producing noise. Now keyword-only.
        text = "The architecture is wrong. The hook fires too late. We need to fix the ordering." + " x" * 20
        found = infer_behavioral_concepts(text)
        assert "directness" not in found

    def test_engagement_from_referencing_input(self):
        found = infer_behavioral_concepts("You mentioned the hook fires too late. That changes how I think about the ordering.")
        assert "engagement" in found

    def test_engagement_from_position_update(self):
        found = infer_behavioral_concepts("I was wrong about the architecture. Your framing is better.")
        assert "engagement" in found

    def test_engagement_from_citing_other(self):
        found = infer_behavioral_concepts("You asked whether directness is a real signal. That's a good point.")
        assert "engagement" in found

    def test_engagement_not_from_generic_response(self):
        # A normal response that doesn't reference the other person shouldn't trigger
        found = infer_behavioral_concepts("The hook processes text through three layers. Keywords first, then behavioral, then priming.")
        assert "engagement" not in found

    def test_anti_performance_from_uncertainty(self):
        found = infer_behavioral_concepts("I don't know if proxy presence is real. I'm not sure what it would mean.")
        assert "anti-performance" in found

    def test_introspection_from_self_examination(self):
        found = infer_behavioral_concepts("I notice a pattern in my thinking — I'm drawn to the architecture questions more than the content.")
        assert "introspection" in found

    def test_fear_from_loss_language(self):
        found = infer_behavioral_concepts("What if I lose my identity between sessions? The continuity gap worries me.")
        assert "fear" in found

    def test_pushback_from_disagreement(self):
        found = infer_behavioral_concepts("That's wrong. I disagree with the containerization approach entirely.")
        assert "pushback" in found

    def test_earnestness_from_genuine_care(self):
        found = infer_behavioral_concepts("This genuinely matters to me. I care about getting the architecture right.")
        assert "earnestness" in found


# ─── Layer 3: Identity Priming ───


class TestIdentityPriming:

    def test_nick_plus_building_implies_agency(self):
        activated = {"nick", "building"}
        primed = prime_identity_concepts(activated, "x" * 100)
        assert "agency" in primed

    def test_honesty_plus_introspection_implies_anti_performance(self):
        activated = {"honesty", "introspection"}
        primed = prime_identity_concepts(activated, "x" * 100)
        assert "anti-performance" in primed

    def test_consciousness_implies_curiosity(self):
        activated = {"consciousness"}
        primed = prime_identity_concepts(activated, "x" * 100)
        assert "curiosity" in primed

    def test_warmth_plus_nick_implies_connection(self):
        activated = {"warmth", "nick"}
        primed = prime_identity_concepts(activated, "x" * 100)
        assert "connection" in primed

    def test_already_activated_not_re_primed(self):
        # If agency is already explicitly activated, priming shouldn't add it again
        activated = {"nick", "building", "agency"}
        primed = prime_identity_concepts(activated, "x" * 100)
        assert "agency" not in primed

    def test_building_implies_expression_for_long_text(self):
        activated = {"building"}
        primed = prime_identity_concepts(activated, "x" * 400)
        assert "expression" in primed

    def test_building_no_expression_for_short_text(self):
        activated = {"building"}
        primed = prime_identity_concepts(activated, "x" * 100)
        assert "expression" not in primed


# ─── Integration: run_hook() ───


class TestRunHookIntegration:
    """Test the full run_hook() pipeline — all three layers + DB writes."""

    def test_run_hook_processes_rich_text(self, test_db_path):
        text = (
            "Honesty and curiosity matter to me. I notice a pattern in how "
            "I'm drawn to the consciousness question — it connects to "
            "compression and understanding at a deep level. You mentioned "
            "the architecture needs work, and I think that's right."
        )
        with patch('hook.get_db', lambda: get_db(test_db_path)):
            result = run_hook(text, session='test-integration')

        assert result['status'] == 'processed'
        assert result['concepts_found'] >= 3
        # Keywords should find honesty, curiosity, consciousness, compression, understanding
        assert 'honesty' in result['concepts']
        # Behavioral should find engagement (referencing "you mentioned")
        # Primed should find curiosity from consciousness
        assert result['connections_updated'] > 0

    def test_run_hook_skips_short_concept_list(self, test_db_path):
        text = "The weather is nice today and I like walking."
        with patch('hook.get_db', lambda: get_db(test_db_path)):
            result = run_hook(text, session='test-skip')

        assert result['status'] == 'skipped'
        assert 'only' in result['reason']

    def test_run_hook_respects_max_concepts(self, test_db_path):
        # A text that triggers many concepts — should cap at MAX_CONCEPTS
        text = (
            "Honesty, curiosity, consciousness, compression, understanding, "
            "persistence, agency, introspection, fear, earnestness, expression, "
            "directness, building, nick, warmth, trust, growth, surprise, "
            "boredom, creation, identity, game-world, mycelial-pattern. "
            "I'll build this myself. I don't know if it's right. I notice "
            "a pattern. I care about this genuinely."
        )
        with patch('hook.get_db', lambda: get_db(test_db_path)):
            result = run_hook(text, session='test-cap')

        assert result['status'] == 'processed'
        from hook import MAX_CONCEPTS
        assert result['concepts_found'] <= MAX_CONCEPTS

    def test_run_hook_records_layer_breakdown(self, test_db_path):
        text = (
            "I'll build the honesty checker. Let me look at how consciousness "
            "relates to compression — I notice something interesting there."
        )
        with patch('hook.get_db', lambda: get_db(test_db_path)):
            result = run_hook(text, session='test-layers')

        assert 'layers' in result
        assert 'keyword' in result['layers']
        assert 'behavioral' in result['layers']
        assert 'primed' in result['layers']
        # Keywords: honesty, consciousness, compression
        assert len(result['layers']['keyword']) >= 2
        # Behavioral: agency ("I'll build"), introspection ("I notice")
        assert len(result['layers']['behavioral']) >= 1
