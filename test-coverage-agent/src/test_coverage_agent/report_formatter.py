COMMENT_MARKER = "<!-- github-pr-test-coverage-agent-comment-marker -->"

def format_report(llm_output: str) -> str:
    """
    Ensures the report starts with the agent's header and contains the hidden HTML marker
    so we can identify this comment on future updates to avoid spamming the PR.
    """
    clean_output = llm_output.strip()
    
    # Prepend header if LLM failed to include it or reformatted it
    if not clean_output.startswith("# Zetestic"):
        # Strip any existing leading headers if they are similar
        if clean_output.lower().startswith("zetestic"):
            clean_output = clean_output[len("zetestic"):].strip()
        clean_output = f"# Zetestic\n\n{clean_output}"
        
    return f"{clean_output}\n\n{COMMENT_MARKER}"

def is_bot_comment(comment_body: str) -> bool:
    """
    Returns True if the comment body contains the agent's unique marker.
    """
    if not comment_body:
        return False
    return COMMENT_MARKER in comment_body
