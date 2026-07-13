import re
from dataclasses import dataclass, field
from typing import Dict, List

from test_coverage_agent.obligation_extractor import TestObligation


@dataclass
class CoverageEvidence:
    """
    The result of searching existing test files for coverage of a single TestObligation.
    Produced entirely by code — no LLM involved.
    """
    obligation_id: str
    status: str              # "covered" | "partial" | "missing"
    matching_tests: List[str] = field(default_factory=list)   # Test function names that matched
    evidence_snippets: List[str] = field(default_factory=list) # Short excerpts proving the match


def search_coverage(
    obligations: List[TestObligation],
    file_contents: Dict[str, str],
) -> Dict[str, CoverageEvidence]:
    """
    For each TestObligation, searches all test files in file_contents for
    evidence that the obligation is already covered.

    Returns a dict keyed by obligation.id -> CoverageEvidence.

    Search strategy per obligation:
      - For each symbol in obligation.symbols, scan every test file for:
          1. A test function name containing the symbol
          2. The symbol appearing as a literal in the test file body
      - Hit count determines status:
          >= 2 distinct hits  -> "covered"
          == 1 distinct hit   -> "partial"
          0 hits              -> "missing"
    """
    # Separate test file contents from source file contents
    test_file_contents = {
        path: content
        for path, content in file_contents.items()
        if _is_test_path(path)
    }

    results: Dict[str, CoverageEvidence] = {}

    for obligation in obligations:
        evidence = _search_single_obligation(obligation, test_file_contents)
        results[obligation.id] = evidence

    return results


def _search_single_obligation(
    obligation: TestObligation,
    test_file_contents: Dict[str, str],
) -> CoverageEvidence:
    """Searches all test files for evidence covering a single obligation."""
    matching_tests: List[str] = []
    evidence_snippets: List[str] = []
    hit_count = 0

    for test_path, content in test_file_contents.items():
        lines = content.splitlines()

        for symbol in obligation.symbols:
            if not symbol:
                continue

            symbol_lower = symbol.lower()

            # --- Check 1: test function name contains the symbol ---
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("def test_") and symbol_lower in stripped.lower():
                    func_name = _extract_function_name(stripped)
                    if func_name and func_name not in matching_tests:
                        matching_tests.append(func_name)
                        snippet = _extract_snippet(lines, i)
                        evidence_snippets.append(f"[{test_path}] {snippet}")
                        hit_count += 1

            # --- Check 2: symbol appears as a word boundary in the file body ---
            # Use word-boundary regex to avoid partial matches (e.g. "divide" in "undivided")
            pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
            body_matches = pattern.findall(content)
            if body_matches:
                hit_count += len(set(body_matches))  # count unique occurrences

        # --- Check 3: search_terms — broader behavioral keywords ---
        # These catch integration tests that don't use the exact function name
        # but do reference the domain concept (e.g. "inactive", "403", "access_token").
        for term in obligation.search_terms:
            if not term:
                continue
            term_pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            term_matches = term_pattern.findall(content)
            if term_matches:
                hit_count += 1  # 1 point per matched term (not per occurrence)

    # Determine status from hit count
    if hit_count >= 2:
        status = "covered"
    elif hit_count == 1:
        status = "partial"
    else:
        status = "missing"

    return CoverageEvidence(
        obligation_id=obligation.id,
        status=status,
        matching_tests=matching_tests,
        evidence_snippets=evidence_snippets,
    )


def _extract_function_name(def_line: str) -> str:
    """Extracts the function name from a 'def func_name(...)' line."""
    match = re.match(r"def\s+(\w+)\s*\(", def_line)
    return match.group(1) if match else ""


def _extract_snippet(lines: List[str], func_def_line_index: int, context_lines: int = 3) -> str:
    """Returns the function signature plus the next few lines as a short excerpt."""
    end = min(func_def_line_index + context_lines + 1, len(lines))
    snippet_lines = lines[func_def_line_index:end]
    return " | ".join(line.strip() for line in snippet_lines if line.strip())


def _is_test_path(path: str) -> bool:
    """Returns True if the path looks like a test file."""
    parts = path.replace("\\", "/").split("/")
    basename = parts[-1]
    return (
        basename.startswith("test_")
        or basename.endswith("_test.py")
        or "tests/" in path
        or "test/" in path
    )


def format_obligations_for_prompt(
    obligations: List[TestObligation],
    evidence: Dict[str, CoverageEvidence],
) -> str:
    """
    Serializes obligations + their coverage evidence into a human-readable text block
    to be embedded in the final report prompt.
    """
    if not obligations:
        return "(No structured test obligations were extracted from this diff.)"

    parts = []
    for ob in obligations:
        ev = evidence.get(ob.id)
        status_str = ev.status if ev else "unknown"
        emoji = {"covered": "✅", "partial": "⚠️", "missing": "❌"}.get(status_str, "❓")

        section = f"Obligation ID: {ob.id}\n"
        section += f"Title: {ob.title}\n"
        section += f"Type: {ob.obligation_type}\n"
        section += f"Source File: {ob.source_file}\n"
        section += f"Symbols: {', '.join(ob.symbols)}\n"
        section += f"Search Terms: {', '.join(ob.search_terms)}\n"
        section += f"Expected Behavior: {ob.expected_behavior}\n"
        section += f"Description: {ob.description}\n"
        section += f"Coverage Status: {emoji} {status_str.capitalize()}\n"

        if ev and ev.matching_tests:
            section += f"Matching Test Functions: {', '.join(ev.matching_tests)}\n"
        if ev and ev.evidence_snippets:
            section += "Evidence:\n"
            for snippet in ev.evidence_snippets[:2]:  # cap at 2 to keep prompt lean
                section += f"  - {snippet}\n"

        parts.append(section)

    return "\n---\n".join(parts)
