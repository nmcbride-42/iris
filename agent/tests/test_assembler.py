"""
Tests for the morning brief assembler (assemble_startup.py).

Covers path derivation, token budgets, differential briefs, and output structure.
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from assemble_startup import (
    read_file, budget_check, is_nap_recovery, file_changed_since_last,
    CHAR_BUDGETS, NAP_THRESHOLD_HOURS,
)


class TestReadFile:

    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello world", encoding="utf-8")
        assert read_file(f) == "hello world"

    def test_returns_empty_for_missing(self, tmp_path):
        assert read_file(tmp_path / "nonexistent.md") == ""

    def test_strips_whitespace(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("  hello  \n\n", encoding="utf-8")
        assert read_file(f) == "hello"


class TestBudgetCheck:

    def test_under_budget_passes_through(self):
        content = "Short content"
        result = budget_check(content, "current")
        assert result == content

    def test_over_budget_truncates(self):
        content = "Line one\nLine two\n" * 500  # ~4500 chars
        result = budget_check(content, "warmstart")  # budget: 3000
        assert len(result) <= CHAR_BUDGETS["warmstart"] + 100  # allow for truncation message
        assert "truncated" in result

    def test_no_budget_passes_through(self):
        content = "x" * 10000
        result = budget_check(content, "opinions")  # not in CHAR_BUDGETS
        assert result == content

    def test_truncates_at_newline_boundary(self):
        content = "a" * 2900 + "\n" + "b" * 200
        result = budget_check(content, "warmstart")  # budget: 3000
        assert result.endswith("truncated — full content in source file]*")
        assert "\nb" not in result.split("[...")[0]


class TestFileChangedSince:

    def test_new_file_counts_as_changed(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("content", encoding="utf-8")
        assert file_changed_since_last(f, {}) is True

    def test_missing_file_counts_as_changed(self, tmp_path):
        assert file_changed_since_last(tmp_path / "gone.md", {}) is True

    def test_unchanged_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("content", encoding="utf-8")
        mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        meta = {str(f): mtime}
        assert file_changed_since_last(f, meta) is False

    def test_modified_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("content", encoding="utf-8")
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        meta = {str(f): old_time}
        assert file_changed_since_last(f, meta) is True


class TestBudgetConstants:

    def test_budgets_exist_for_operational_sections(self):
        assert "current" in CHAR_BUDGETS
        assert "warmstart" in CHAR_BUDGETS
        assert "resonance" in CHAR_BUDGETS

    def test_no_budgets_for_identity(self):
        # Identity sections should NOT have budgets
        assert "opinions" not in CHAR_BUDGETS
        assert "wants" not in CHAR_BUDGETS
        assert "likes" not in CHAR_BUDGETS

    def test_nap_threshold_is_reasonable(self):
        assert 1 <= NAP_THRESHOLD_HOURS <= 12
