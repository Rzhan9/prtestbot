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
