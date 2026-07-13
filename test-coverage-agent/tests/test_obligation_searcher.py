import sys
import os

# Ensure src/ is on the path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import pytest

from test_coverage_agent.obligation_extractor import TestObligation
from test_coverage_agent.obligation_searcher import (
    CoverageEvidence,
    search_coverage,
    format_obligations_for_prompt,
    _is_test_path,
    _extract_function_name,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_obligation(id="div-zero", symbols=None, search_terms=None, source_file="src/division.py"):
    return TestObligation(
        id=id,
        title="Test title",
        description="Test description",
        source_file=source_file,
        symbols=symbols or ["div"],
        search_terms=search_terms or [],
        expected_behavior="div(x, 0) raises ZeroDivisionError.",
        obligation_type="error_handling",
    )


# ── _is_test_path ─────────────────────────────────────────────────────────────

def test_is_test_path_recognises_test_file():
    assert _is_test_path("tests/test_division.py") is True

def test_is_test_path_rejects_source_file():
    assert _is_test_path("src/division.py") is False


# ── _extract_function_name ────────────────────────────────────────────────────

def test_extract_function_name_simple():
    assert _extract_function_name("def test_divide_by_zero():") == "test_divide_by_zero"

def test_extract_function_name_with_args():
    assert _extract_function_name("def test_foo(self, x):") == "test_foo"

def test_extract_function_name_no_match():
    assert _extract_function_name("class Foo:") == ""


# ── search_coverage ───────────────────────────────────────────────────────────

TEST_FILE_CONTENT = """\
import pytest
from src.division import div

def test_div_normal():
    assert div(10, 2) == 5

def test_div_zero_raises():
    with pytest.raises(ZeroDivisionError):
        div(10, 0)
"""

def test_search_coverage_finds_covered_obligation():
    ob = make_obligation(symbols=["div"])
    evidence = search_coverage([ob], {"tests/test_division.py": TEST_FILE_CONTENT})
    ev = evidence["div-zero"]
    # "div" appears in test function names and in the import — 2+ hits → covered
    assert ev.status == "covered"
    assert ev.obligation_id == "div-zero"

def test_search_coverage_missing_when_no_test_files():
    ob = make_obligation(symbols=["div"])
    # Only source files, no test files
    evidence = search_coverage([ob], {"src/division.py": "def div(n1, n2): ..."})
    assert evidence["div-zero"].status == "missing"

def test_search_coverage_missing_when_symbol_not_found():
    ob = make_obligation(symbols=["totally_unknown_symbol_xyz"], search_terms=[])
    evidence = search_coverage([ob], {"tests/test_division.py": TEST_FILE_CONTENT})
    assert evidence["div-zero"].status == "missing"

def test_search_coverage_finds_via_search_terms():
    """search_terms should catch tests that reference a concept but not the exact function."""
    test_content = """\
def test_zero_denominator_blocked():
    # denominator must not be zero
    result = safe_divide(10, 0)
    assert result is None
"""
    ob = make_obligation(
        symbols=["totally_unknown_func"],  # symbol won't match
        search_terms=["denominator", "safe_divide"],  # both appear as whole words in the body
    )
    evidence = search_coverage([ob], {"tests/test_math.py": test_content})
    # "denominator" in comment + "safe_divide" in body -> 2 search_term hits -> covered
    assert evidence["div-zero"].status == "covered"

def test_search_coverage_multiple_obligations():
    ob1 = make_obligation(id="ob1", symbols=["div"])
    ob2 = make_obligation(id="ob2", symbols=["totally_unknown_xyz"])
    evidence = search_coverage(
        [ob1, ob2],
        {"tests/test_division.py": TEST_FILE_CONTENT}
    )
    assert evidence["ob1"].status == "covered"
    assert evidence["ob2"].status == "missing"

def test_search_coverage_captures_matching_test_functions():
    ob = make_obligation(symbols=["div"])
    evidence = search_coverage([ob], {"tests/test_division.py": TEST_FILE_CONTENT})
    ev = evidence["div-zero"]
    # Both test functions contain "div"
    assert any("div" in fn for fn in ev.matching_tests)

def test_search_coverage_empty_obligations():
    evidence = search_coverage([], {"tests/test_division.py": TEST_FILE_CONTENT})
    assert evidence == {}


# ── format_obligations_for_prompt ─────────────────────────────────────────────

def test_format_obligations_empty():
    result = format_obligations_for_prompt([], {})
    assert "No structured" in result

def test_format_obligations_includes_title_and_status():
    ob = make_obligation()
    ev = CoverageEvidence(obligation_id="div-zero", status="missing")
    result = format_obligations_for_prompt([ob], {"div-zero": ev})
    assert "div-zero" in result
    assert "Missing" in result
    assert "❌" in result

def test_format_obligations_covered_shows_checkmark():
    ob = make_obligation()
    ev = CoverageEvidence(obligation_id="div-zero", status="covered")
    result = format_obligations_for_prompt([ob], {"div-zero": ev})
    assert "✅" in result

def test_format_obligations_partial_shows_warning():
    ob = make_obligation()
    ev = CoverageEvidence(obligation_id="div-zero", status="partial")
    result = format_obligations_for_prompt([ob], {"div-zero": ev})
    assert "⚠️" in result
