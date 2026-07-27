import os
import sys
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from test_coverage_agent.report_formatter import format_report, is_bot_comment, COMMENT_MARKER

def test_format_report_no_header():
    llm_output = "## Verdict\nSufficient\n\nSome behavior summary."
    formatted = format_report(llm_output)
    
    assert formatted.startswith("# Zetestic")
    assert COMMENT_MARKER in formatted
    assert "Sufficient" in formatted

def test_format_report_with_header():
    llm_output = "# Zetestic\n\n## Verdict\nSufficient\n\nSome behavior summary."
    formatted = format_report(llm_output)
    
    assert formatted.startswith("# Zetestic\n\n## Verdict")
    assert COMMENT_MARKER in formatted

def test_is_bot_comment():
    assert is_bot_comment(f"Some comment content\n\n{COMMENT_MARKER}") is True
    assert is_bot_comment("Some other random comment") is False
    assert is_bot_comment("") is False
    assert is_bot_comment(None) is False

def test_format_report_score_section_shown():
    """Score section appears when obligations exist."""
    formatted = format_report("## Verdict\nSufficient", covered=7, total=10)
    assert "## Coverage Score" in formatted
    assert "**7/10**" in formatted

def test_format_report_score_section_description():
    """Score section contains the description and guidance text."""
    formatted = format_report("## Verdict\nSufficient", covered=3, total=5)
    assert "fully covered by existing tests" in formatted
    assert "To raise this score" in formatted

def test_format_report_score_section_perfect():
    """Perfect score (all covered) is rendered correctly."""
    formatted = format_report("## Verdict\nSufficient", covered=4, total=4)
    assert "**4/4**" in formatted

def test_format_report_no_score_when_no_obligations():
    """No score section when total is 0 or omitted (test-only / no-obligation PRs)."""
    formatted_zero = format_report("## Verdict\nSufficient", covered=0, total=0)
    formatted_none = format_report("## Verdict\nSufficient")
    assert "## Coverage Score" not in formatted_zero
    assert "## Coverage Score" not in formatted_none

def test_format_report_score_before_marker():
    """Score section must appear before the hidden comment marker."""
    formatted = format_report("## Verdict\nSufficient", covered=2, total=3)
    score_pos = formatted.index("## Coverage Score")
    marker_pos = formatted.index(COMMENT_MARKER)
    assert score_pos < marker_pos
