COMMENT_MARKER = "<!-- github-pr-test-coverage-agent-comment-marker -->"

def format_report(llm_output: str, covered: int = None, total: int = None) -> str:
    """
    Ensures the report starts with the agent's header and contains the hidden HTML marker
    so we can identify this comment on future updates to avoid spamming the PR.

    covered: number of obligations with status 'covered'.
    total:   total number of obligations extracted.
    When total > 0, a Coverage Score section is appended after the LLM body.
    When total is 0 or None (no obligations), no score section is shown.
    """
    clean_output = llm_output.strip()
    
    # Prepend header if LLM failed to include it or reformatted it
    if not clean_output.startswith("# Zetestic"):
        # Strip any existing leading headers if they are similar
        if clean_output.lower().startswith("zetestic"):
            clean_output = clean_output[len("zetestic"):].strip()
        clean_output = f"# Zetestic\n\n{clean_output}"

    score_section = ""
    if total:  # only when there are obligations (total > 0 and not None)
        score_section = (
            f"\n\n---\n\n"
            f"## Coverage Score\n\n"
            f"**{covered}/{total}**\n\n"
            f"This score reflects how many of the {total} test obligation(s) identified in this PR "
            f"are fully covered by existing tests. Each obligation earns 1 point only when it is "
            f"completely satisfied — partial coverage does not count. "
            f"To raise this score, add or update tests so that the missing or partial obligations "
            f"listed above are fully covered."
        )

    return f"{clean_output}{score_section}\n\n{COMMENT_MARKER}"

def is_bot_comment(comment_body: str) -> bool:
    """
    Returns True if the comment body contains the agent's unique marker.
    """
    if not comment_body:
        return False
    return COMMENT_MARKER in comment_body
