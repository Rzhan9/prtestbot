import os
import sys
import json
from unittest.mock import patch, MagicMock

# Configure sys.path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from test_coverage_agent.main import main
from test_coverage_agent.llm_provider import LlmProvider

class DummyProvider(LlmProvider):
    def __init__(self):
        self.model = "dummy"
        
    def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        return """# Zetestic

## Verdict

Partially sufficient

## Summary of Changed Behavior

* Test summary

## Existing Relevant Tests Found

* None

## Missing or Partial Test Obligations

* None

## Notes / Uncertainty

* None"""

@patch("test_coverage_agent.main.get_llm_provider")
@patch("test_coverage_agent.main.read_file_content")
@patch("test_coverage_agent.main.find_related_tests")
@patch("test_coverage_agent.main.GitHubClient")
def test_main_flow(mock_github_client_class, mock_find_related_tests, mock_read_file_content, mock_get_llm_provider, tmp_path):
    # Setup mock LLM and test finder
    mock_get_llm_provider.return_value = DummyProvider()
    mock_find_related_tests.return_value = ["tests/test_calc.py"]
    
    # Setup mock repo analyzer content reading
    def read_file_side_effect(filename, repo_root):
        if "calc.py" in filename:
            return "def add(a, b): return a + b\ndef divide(a, b): return a / b"
        if "test_calc.py" in filename:
            return "def test_add(): pass"
        return None
    mock_read_file_content.side_effect = read_file_side_effect
    
    # Mock GitHubClient instance and APIs
    mock_gh_client = MagicMock()
    mock_github_client_class.return_value = mock_gh_client
    
    mock_gh_client.get_pr_details.return_value = {
        "title": "Mock Title",
        "body": "Mock Body",
        "draft": False
    }
    
    # PR Diff showing adding the divide function
    mock_gh_client.get_pr_diff.return_value = """diff --git a/src/calc.py b/src/calc.py
index a1b2c3d..e4f5g6h 100644
--- a/src/calc.py
+++ b/src/calc.py
@@ -1,3 +1,7 @@
 def add(a, b):
     return a + b
+
+def divide(a, b):
+    return a / b
"""
    mock_gh_client.get_pr_comments.return_value = []
    
    # Setup mock GITHUB_EVENT_PATH file
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({
        "pull_request": {
            "number": 12,
            "title": "Mock Title",
            "body": "Mock Body",
            "draft": False
        },
        "repository": {
            "full_name": "owner/repo"
        }
    }))
    
    # Execute orchestrator with mocked environment
    with patch.dict(os.environ, {
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_TOKEN": "mock_token",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_WORKSPACE": str(tmp_path)
    }):
        main()
        
    # Verify PR comment creation was called with correct arguments
    mock_gh_client.create_comment.assert_called_once()
    args, kwargs = mock_gh_client.create_comment.call_args
    assert args[0] == 12
    assert "Zetestic" in args[1]
    assert "Partially sufficient" in args[1]
    assert "<!-- github-pr-test-coverage-agent-comment-marker -->" in args[1]


@patch("test_coverage_agent.main.get_llm_provider")
@patch("test_coverage_agent.main.read_file_content")
@patch("test_coverage_agent.main.find_related_tests")
@patch("test_coverage_agent.main.GitHubClient")
def test_main_flow_update_comment(mock_github_client_class, mock_find_related_tests, mock_read_file_content, mock_get_llm_provider, tmp_path):
    # Setup mock LLM and test finder
    mock_get_llm_provider.return_value = DummyProvider()
    mock_find_related_tests.return_value = []
    mock_read_file_content.return_value = None
    
    # Mock GitHubClient
    mock_gh_client = MagicMock()
    mock_github_client_class.return_value = mock_gh_client
    
    mock_gh_client.get_pr_details.return_value = {
        "title": "Mock Title",
        "body": "Mock Body",
        "draft": False
    }
    mock_gh_client.get_pr_diff.return_value = """diff --git a/src/calc.py b/src/calc.py
new file mode 100644
--- /dev/null
+++ b/src/calc.py
@@ -0,0 +1,2 @@
+def add(a, b):
+    return a + b
"""
    # Return an existing comment with the agent's tracking marker
    mock_gh_client.get_pr_comments.return_value = [
        {"id": 111, "body": "Some random user comment"},
        {"id": 222, "body": "Previous report\n\n<!-- github-pr-test-coverage-agent-comment-marker -->"}
    ]
    
    # Setup mock GITHUB_EVENT_PATH file
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({
        "pull_request": {
            "number": 12,
            "title": "Mock Title",
            "body": "Mock Body",
            "draft": False
        },
        "repository": {
            "full_name": "owner/repo"
        }
    }))
    
    # Execute orchestrator
    with patch.dict(os.environ, {
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_TOKEN": "mock_token",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_WORKSPACE": str(tmp_path)
    }):
        main()
        
    # Verify create_comment was NOT called
    mock_gh_client.create_comment.assert_not_called()
    
    # Verify update_comment was called on the correct comment ID 222
    mock_gh_client.update_comment.assert_called_once()
    args, kwargs = mock_gh_client.update_comment.call_args
    assert args[0] == 222
    assert "Zetestic" in args[1]
    assert "Partially sufficient" in args[1]


# ---------------------------------------------------------------------------
# Coverage threshold tests
# ---------------------------------------------------------------------------

def _make_event_file(tmp_path):
    """Helper: write a minimal PR event JSON and return its path."""
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps({
        "pull_request": {
            "number": 12,
            "title": "Test PR",
            "body": "",
            "draft": False,
        },
        "repository": {"full_name": "owner/repo"},
    }))
    return event_file


def _source_diff():
    return """\
diff --git a/myapp/calc.py b/myapp/calc.py
new file mode 100644
--- /dev/null
+++ b/myapp/calc.py
@@ -0,0 +1,2 @@
+def add(a, b):
+    return a + b
"""


@patch("test_coverage_agent.main.search_coverage")
@patch("test_coverage_agent.main.extract_obligations")
@patch("test_coverage_agent.main.get_llm_provider")
@patch("test_coverage_agent.main.read_file_content")
@patch("test_coverage_agent.main.find_related_tests")
@patch("test_coverage_agent.main.GitHubClient")
def test_main_fails_when_coverage_below_threshold(
    mock_gh_class, mock_find, mock_read, mock_llm,
    mock_extract, mock_search, tmp_path
):
    """main() should exit with code 1 when covered/total < 70%."""
    from test_coverage_agent.obligation_extractor import TestObligation
    from test_coverage_agent.obligation_searcher import CoverageEvidence

    # Two obligations, zero covered → 0% < 70% → should fail
    ob1 = TestObligation(id="a", title="A", description="", source_file="src/calc.py",
                         symbols=["add"], search_terms=[], expected_behavior="", obligation_type="new_behavior")
    ob2 = TestObligation(id="b", title="B", description="", source_file="src/calc.py",
                         symbols=["sub"], search_terms=[], expected_behavior="", obligation_type="new_behavior")
    mock_extract.return_value = [ob1, ob2]
    mock_search.return_value = {
        "a": CoverageEvidence(obligation_id="a", status="missing"),
        "b": CoverageEvidence(obligation_id="b", status="missing"),
    }
    mock_llm.return_value = DummyProvider()
    mock_find.return_value = []
    mock_read.return_value = "def add(a, b): return a + b"  # non-None → source file enters source_file_contents

    mock_gh_client = MagicMock()
    mock_gh_class.return_value = mock_gh_client
    mock_gh_client.get_pr_details.return_value = {"title": "T", "body": "", "draft": False}
    mock_gh_client.get_pr_diff.return_value = _source_diff()
    mock_gh_client.get_pr_comments.return_value = []

    event_file = _make_event_file(tmp_path)

    import pytest
    with patch.dict(os.environ, {
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_TOKEN": "tok",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_WORKSPACE": str(tmp_path),
    }):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 1
    # Comment must still have been posted before the exit
    mock_gh_client.create_comment.assert_called_once()


@patch("test_coverage_agent.main.search_coverage")
@patch("test_coverage_agent.main.extract_obligations")
@patch("test_coverage_agent.main.get_llm_provider")
@patch("test_coverage_agent.main.read_file_content")
@patch("test_coverage_agent.main.find_related_tests")
@patch("test_coverage_agent.main.GitHubClient")
def test_main_passes_when_coverage_meets_threshold(
    mock_gh_class, mock_find, mock_read, mock_llm,
    mock_extract, mock_search, tmp_path
):
    """main() should NOT exit with code 1 when covered/total >= 70%."""
    from test_coverage_agent.obligation_extractor import TestObligation
    from test_coverage_agent.obligation_searcher import CoverageEvidence

    # Three obligations, all covered → 100% >= 70% → should pass
    obs = [
        TestObligation(id=f"ob{i}", title=f"Ob{i}", description="", source_file="src/calc.py",
                       symbols=["add"], search_terms=[], expected_behavior="", obligation_type="new_behavior")
        for i in range(3)
    ]
    mock_extract.return_value = obs
    mock_search.return_value = {
        ob.id: CoverageEvidence(obligation_id=ob.id, status="covered") for ob in obs
    }
    mock_llm.return_value = DummyProvider()
    mock_find.return_value = []
    mock_read.return_value = None

    mock_gh_client = MagicMock()
    mock_gh_class.return_value = mock_gh_client
    mock_gh_client.get_pr_details.return_value = {"title": "T", "body": "", "draft": False}
    mock_gh_client.get_pr_diff.return_value = _source_diff()
    mock_gh_client.get_pr_comments.return_value = []

    event_file = _make_event_file(tmp_path)

    with patch.dict(os.environ, {
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_TOKEN": "tok",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_WORKSPACE": str(tmp_path),
    }):
        main()  # should complete without raising SystemExit

    mock_gh_client.create_comment.assert_called_once()


@patch("test_coverage_agent.main.search_coverage")
@patch("test_coverage_agent.main.extract_obligations")
@patch("test_coverage_agent.main.get_llm_provider")
@patch("test_coverage_agent.main.read_file_content")
@patch("test_coverage_agent.main.find_related_tests")
@patch("test_coverage_agent.main.GitHubClient")
def test_main_passes_at_exactly_70_percent(
    mock_gh_class, mock_find, mock_read, mock_llm,
    mock_extract, mock_search, tmp_path
):
    """main() should pass at exactly 70% coverage (7/10). Threshold is strict < 0.70."""
    from test_coverage_agent.obligation_extractor import TestObligation
    from test_coverage_agent.obligation_searcher import CoverageEvidence

    # 10 obligations, 7 covered → exactly 70% → should pass
    obs = [
        TestObligation(id=f"ob{i}", title=f"Ob{i}", description="", source_file="myapp/calc.py",
                       symbols=["add"], search_terms=[], expected_behavior="", obligation_type="new_behavior")
        for i in range(10)
    ]
    mock_extract.return_value = obs
    mock_search.return_value = {
        ob.id: CoverageEvidence(
            obligation_id=ob.id,
            status="covered" if i < 7 else "missing"
        )
        for i, ob in enumerate(obs)
    }
    mock_llm.return_value = DummyProvider()
    mock_find.return_value = []
    mock_read.return_value = "def add(a, b): return a + b"

    mock_gh_client = MagicMock()
    mock_gh_class.return_value = mock_gh_client
    mock_gh_client.get_pr_details.return_value = {"title": "T", "body": "", "draft": False}
    mock_gh_client.get_pr_diff.return_value = _source_diff()
    mock_gh_client.get_pr_comments.return_value = []

    event_file = _make_event_file(tmp_path)

    with patch.dict(os.environ, {
        "GITHUB_EVENT_PATH": str(event_file),
        "GITHUB_TOKEN": "tok",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_WORKSPACE": str(tmp_path),
    }):
        main()  # should complete without raising SystemExit

    mock_gh_client.create_comment.assert_called_once()
