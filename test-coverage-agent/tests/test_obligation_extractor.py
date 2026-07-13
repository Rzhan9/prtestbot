import sys
import os

# Ensure src/ is on the path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import json
import pytest
from unittest.mock import MagicMock

from test_coverage_agent.obligation_extractor import (
    TestObligation,
    extract_obligations,
    _parse_obligations,
    _is_test_path,
)


# ── _is_test_path ────────────────────────────────────────────────────────────

def test_is_test_path_detects_test_prefix():
    assert _is_test_path("tests/test_calc.py") is True

def test_is_test_path_detects_test_suffix():
    assert _is_test_path("calc_test.py") is True

def test_is_test_path_rejects_source_file():
    assert _is_test_path("src/calc.py") is False

def test_is_test_path_rejects_non_python():
    assert _is_test_path("README.md") is False


# ── _parse_obligations ────────────────────────────────────────────────────────

VALID_JSON = json.dumps([
    {
        "id": "div-zero",
        "title": "ZeroDivisionError guard",
        "description": "div() must raise ZeroDivisionError when n2 is 0.",
        "source_file": "math/division.py",
        "symbols": ["div"],
        "search_terms": ["zero", "ZeroDivisionError"],
        "expected_behavior": "Calling div(x, 0) raises ZeroDivisionError.",
        "obligation_type": "error_handling",
    }
])

def test_parse_obligations_valid_json():
    result = _parse_obligations(VALID_JSON)
    assert len(result) == 1
    ob = result[0]
    assert isinstance(ob, TestObligation)
    assert ob.id == "div-zero"
    assert ob.title == "ZeroDivisionError guard"
    assert ob.symbols == ["div"]
    assert ob.search_terms == ["zero", "ZeroDivisionError"]
    assert ob.expected_behavior == "Calling div(x, 0) raises ZeroDivisionError."
    assert ob.obligation_type == "error_handling"

def test_parse_obligations_strips_markdown_fences():
    fenced = f"```json\n{VALID_JSON}\n```"
    result = _parse_obligations(fenced)
    assert len(result) == 1
    assert result[0].id == "div-zero"

def test_parse_obligations_empty_array():
    result = _parse_obligations("[]")
    assert result == []

def test_parse_obligations_malformed_json_returns_empty():
    result = _parse_obligations("not json at all {{{")
    assert result == []

def test_parse_obligations_non_array_returns_empty():
    result = _parse_obligations('{"id": "x"}')
    assert result == []

def test_parse_obligations_skips_items_with_missing_keys():
    # Missing search_terms, expected_behavior, and obligation_type
    bad_item = json.dumps([{"id": "x", "title": "y"}])
    result = _parse_obligations(bad_item)
    assert result == []

def test_parse_obligations_skips_non_dict_items():
    good = {
        "id": "x", "title": "y", "description": "d",
        "source_file": "f.py", "symbols": [],
        "search_terms": [], "expected_behavior": "e.",
        "obligation_type": "new_behavior"
    }
    mixed = json.dumps(["not a dict", good])
    result = _parse_obligations(mixed)
    assert len(result) == 1


# ── extract_obligations ───────────────────────────────────────────────────────

def test_extract_obligations_returns_parsed_list():
    mock_provider = MagicMock()
    mock_provider.generate_response.return_value = VALID_JSON

    result = extract_obligations(
        unified_diff="diff --git ...",
        file_contents={"math/division.py": "def div(n1, n2):\n    return n1 / n2"},
        provider=mock_provider,
        pr_title="Fix division",
        pr_body="",
    )

    assert len(result) == 1
    assert result[0].id == "div-zero"
    # LLM should have been called exactly once
    mock_provider.generate_response.assert_called_once()

def test_extract_obligations_excludes_test_files_from_prompt():
    """Test files should not appear in the obligation extraction prompt."""
    mock_provider = MagicMock()
    mock_provider.generate_response.return_value = "[]"

    extract_obligations(
        unified_diff="",
        file_contents={
            "src/calc.py": "def add(a, b): return a + b",
            "tests/test_calc.py": "def test_add(): assert add(1,2)==3",
        },
        provider=mock_provider,
    )

    call_args = mock_provider.generate_response.call_args
    user_prompt = call_args[0][1]  # positional arg index 1
    assert "tests/test_calc.py" not in user_prompt
    assert "src/calc.py" in user_prompt

def test_extract_obligations_llm_failure_returns_empty():
    mock_provider = MagicMock()
    mock_provider.generate_response.side_effect = RuntimeError("API down")

    result = extract_obligations(
        unified_diff="",
        file_contents={},
        provider=mock_provider,
    )
    assert result == []
