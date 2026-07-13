import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from test_coverage_agent.llm_provider import LlmProvider


@dataclass
class TestObligation:
    """
    Represents a single behavioral change in the PR that requires a test.
    Produced by LLM call #1 and enriched by the obligation searcher before
    being passed to the final report LLM call.
    """
    id: str                          # Unique slug, e.g. "div-zero-check"
    title: str                       # Short human-readable name
    description: str                 # What behavior must be tested and why
    source_file: str                 # The changed source file this relates to
    symbols: List[str]               # Exact function/class names for code-level search
    search_terms: List[str]          # Broader behavioral keywords for body-level search
    expected_behavior: str           # One sentence: what the test must assert
    obligation_type: str             # new_behavior | edge_case | error_handling | regression


OBLIGATION_EXTRACTION_SYSTEM_PROMPT = """\
You are a test obligation extractor for a PR review pipeline.

Given a unified diff and the current source code of changed files, identify every
behavioral change that requires a new or updated test.

RULES:
- Focus only on behavior: new logic, changed logic, error handling, edge cases.
- Do NOT flag style, formatting, comments, or documentation changes.
- Do NOT flag changes that are clearly already covered if the test file is provided.
- Each obligation must relate to exactly one behavioral change — be specific.
- Symbols should be the exact function or class name(s) involved as they appear in code.
- Obligation types: new_behavior, edge_case, error_handling, regression.

OUTPUT FORMAT:
Respond with a raw JSON array only. No markdown, no prose, no code fences.
Each element must have exactly these keys:
  id               (string, short slug using hyphens)
  title            (string, ≤10 words)
  description      (string, 1-2 sentences explaining what must be tested)
  source_file      (string, relative path to the changed source file)
  symbols          (array of strings, exact function/class names as they appear in code)
  search_terms     (array of strings, broader behavioral keywords that might appear in test
                   bodies — e.g. error messages, status codes, domain concepts)
  expected_behavior (string, one sentence: what the test must assert)
  obligation_type  (string, one of: new_behavior, edge_case, error_handling, regression)

Example:
[
  {
    "id": "inactive-user-login",
    "title": "Inactive users cannot log in",
    "description": "The login flow now rejects inactive users before issuing a token. This must be tested to confirm no token is returned for inactive accounts.",
    "source_file": "src/auth/login.py",
    "symbols": ["login_user", "is_active"],
    "search_terms": ["inactive", "disabled", "403", "access_token", "login"],
    "expected_behavior": "Inactive user with valid credentials receives 403 and no access token.",
    "obligation_type": "error_handling"
  }
]

If there are no behavioral changes that require tests, output an empty array: []
"""


def build_obligation_extraction_prompt(
    unified_diff: str,
    file_contents: Dict[str, str],
    pr_title: str = "",
    pr_body: str = "",
) -> str:
    """
    Builds the focused user prompt for LLM call #1 (obligation extraction).
    Only includes the diff and source files — test files are deliberately excluded
    here because obligation extraction is about what *should* be tested, not what is.
    """
    source_context_parts = []
    for filename, content in file_contents.items():
        source_context_parts.append(f"=== {filename} ===\n{content}")
    source_context = "\n\n".join(source_context_parts)

    return f"""\
PR Title: {pr_title or "(none)"}
PR Description: {pr_body or "(none)"}

Unified Diff:
{unified_diff}

Source Files (current state after PR changes):
{source_context or "(no source file contents available)"}
"""


def extract_obligations(
    unified_diff: str,
    file_contents: Dict[str, str],
    provider: LlmProvider,
    pr_title: str = "",
    pr_body: str = "",
) -> List[TestObligation]:
    """
    LLM call #1: Extracts structured TestObligation objects from the PR diff.

    On any error (LLM failure, malformed JSON, unexpected schema), logs a warning
    and returns an empty list so the pipeline degrades gracefully to the existing
    single-prompt behaviour.
    """
    # Only pass source files (not test files) to the obligation extractor
    source_only_contents = {
        path: content
        for path, content in file_contents.items()
        if not _is_test_path(path)
    }

    user_prompt = build_obligation_extraction_prompt(
        unified_diff=unified_diff,
        file_contents=source_only_contents,
        pr_title=pr_title,
        pr_body=pr_body,
    )

    try:
        raw_response = provider.generate_response(
            OBLIGATION_EXTRACTION_SYSTEM_PROMPT, user_prompt
        )
    except Exception as e:
        print(f"Warning: Obligation extraction LLM call failed: {e}. Continuing without obligations.")
        return []

    return _parse_obligations(raw_response)


def _parse_obligations(raw_response: str) -> List[TestObligation]:
    """
    Parses the LLM's raw text response into a list of TestObligation objects.
    Strips markdown code fences if the LLM wrapped the JSON despite instructions.
    Returns an empty list on any parse or validation error.
    """
    text = raw_response.strip()

    # Strip markdown code fences if present (defensive — LLM may disobey)
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (``` or ```json) and last line (```)
        text = "\n".join(lines[1:-1]).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Warning: Obligation extractor returned malformed JSON: {e}. Skipping obligations.")
        return []

    if not isinstance(data, list):
        print("Warning: Obligation extractor did not return a JSON array. Skipping obligations.")
        return []

    obligations = []
    required_keys = {"id", "title", "description", "source_file", "symbols",
                     "search_terms", "expected_behavior", "obligation_type"}
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"Warning: Obligation #{i} is not an object, skipping.")
            continue
        missing = required_keys - item.keys()
        if missing:
            print(f"Warning: Obligation #{i} missing keys {missing}, skipping.")
            continue
        try:
            obligations.append(TestObligation(
                id=str(item["id"]),
                title=str(item["title"]),
                description=str(item["description"]),
                source_file=str(item["source_file"]),
                symbols=[str(s) for s in item["symbols"]] if isinstance(item["symbols"], list) else [],
                search_terms=[str(s) for s in item["search_terms"]] if isinstance(item["search_terms"], list) else [],
                expected_behavior=str(item["expected_behavior"]),
                obligation_type=str(item["obligation_type"]),
            ))
        except Exception as e:
            print(f"Warning: Could not construct TestObligation for item #{i}: {e}. Skipping.")

    return obligations


def _is_test_path(path: str) -> bool:
    """Returns True if the path looks like a test file."""
    import os
    parts = path.replace("\\", "/").split("/")
    basename = parts[-1]
    return (
        basename.startswith("test_")
        or basename.endswith("_test.py")
        or "tests/" in path
        or "test/" in path
    )
