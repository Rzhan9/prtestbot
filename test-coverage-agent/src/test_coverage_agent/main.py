import os
import sys

# Add the 'src' directory to sys.path to allow running main.py directly
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import json
from dotenv import load_dotenv

from test_coverage_agent.github_client import GitHubClient
from test_coverage_agent.diff_parser import parse_diff
from test_coverage_agent.test_finder import find_related_tests
from test_coverage_agent.repo_analyzer import read_file_content
from test_coverage_agent.llm_provider import get_llm_provider
from test_coverage_agent.prompt_builder import build_user_prompt, SYSTEM_PROMPT
from test_coverage_agent.report_formatter import format_report, is_bot_comment

def main():
    # Load environment variables from .env file for local development
    load_dotenv()
    
    # 1. Parse GitHub Action and local environment variables
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repository = os.environ.get("GITHUB_REPOSITORY")
    
    pr_number = None
    pr_title = ""
    pr_body = ""
    is_draft = False
    repo_name = github_repository
    
    # Read GITHUB_EVENT_PATH if available
    if event_path and os.path.exists(event_path):
        print(f"Reading event payload from: {event_path}")
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                event = json.load(f)
            
            if "pull_request" in event:
                pr = event["pull_request"]
                pr_number = pr.get("number")
                pr_title = pr.get("title", "")
                pr_body = pr.get("body", "")
                is_draft = pr.get("draft", False)
            if "repository" in event:
                repo_name = event["repository"].get("full_name", repo_name)
        except Exception as e:
            print(f"Warning: Failed to parse event JSON file: {e}")
            
    # Support environment variable overrides (highly useful for local verification)
    if os.environ.get("PR_NUMBER"):
        pr_number = int(os.environ.get("PR_NUMBER"))
    if os.environ.get("PR_TITLE"):
        pr_title = os.environ.get("PR_TITLE")
    if os.environ.get("PR_BODY"):
        pr_body = os.environ.get("PR_BODY")
    if os.environ.get("PR_DRAFT"):
        is_draft = os.environ.get("PR_DRAFT").lower() in ("true", "1")
        
    # Exiting early if the PR is in a draft state
    if is_draft:
        print("PR is a draft. Skipping test coverage review.")
        sys.exit(0)
        
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    print(f"Repository root: {repo_root}")
    
    local_mode = not github_token
    if local_mode:
        print("GITHUB_TOKEN not set. Running in LOCAL (dry-run) mode.")
        
    diff_content = ""
    if local_mode:
        local_diff_path = os.environ.get("LOCAL_DIFF_PATH")
        if local_diff_path and os.path.exists(local_diff_path):
            with open(local_diff_path, "r", encoding="utf-8") as f:
                diff_content = f.read()
        else:
            print("Error: GITHUB_TOKEN or LOCAL_DIFF_PATH must be provided to run. Exiting.")
            sys.exit(1)
    else:
        if not pr_number:
            print("Error: PR number could not be determined. Exiting.")
            sys.exit(1)
        if not repo_name:
            print("Error: Repository name could not be determined. Exiting.")
            sys.exit(1)
            
        print(f"Initializing GitHub client for {repo_name}, PR #{pr_number}...")
        gh_client = GitHubClient(github_token, repo_name)
        
        try:
            # Sync metadata from real API
            pr_details = gh_client.get_pr_details(pr_number)
            pr_title = pr_details.get("title", pr_title)
            pr_body = pr_details.get("body", pr_body)
            if pr_details.get("draft"):
                print("PR is a draft (verified via API). Skipping.")
                sys.exit(0)
        except Exception as e:
            print(f"Warning: Failed to fetch PR details from API: {e}. Using event metadata.")
            
        try:
            diff_content = gh_client.get_pr_diff(pr_number)
        except Exception as e:
            print(f"Error fetching PR diff from GitHub: {e}")
            sys.exit(1)

    # 2. Parse raw unified diff
    changed_files = parse_diff(diff_content)
    if not changed_files:
        print("No files changed in this PR. Exiting.")
        sys.exit(0)
        
    print(f"Found {len(changed_files)} changed files in PR:")
    for f in changed_files:
        print(f"- {f.filename} ({f.status})")

    # 3. Read file contents and match existing tests
    file_contents = {}
    related_tests = {}
    changed_files_data = []
    
    for f in changed_files:
        filename = f.filename
        
        file_info = {
            "filename": filename,
            "status": f.status,
            "is_test": f.is_test_file
        }
        changed_files_data.append(file_info)
        
        # If deleted, we don't have code contents
        if f.status == "deleted":
            continue
            
        content = read_file_content(filename, repo_root)
        if content is not None:
            file_contents[filename] = content
            
        if f.is_source_file:
            matched_tests = find_related_tests(filename, repo_root)
            related_tests[filename] = matched_tests
            
            # Read contents of matched tests to supply to the LLM
            for test_file in matched_tests:
                if test_file not in file_contents:
                    test_content = read_file_content(test_file, repo_root)
                    if test_content is not None:
                        file_contents[test_file] = test_content

    # 4. Generate coverage review report using selected LLM Provider
    try:
        provider = get_llm_provider()
        print(f"Loaded LLM Provider: {provider.__class__.__name__} (Model: {provider.model})")
    except Exception as e:
        print(f"Error initializing LLM provider: {e}")
        sys.exit(1)
        
    user_prompt = build_user_prompt(
        pr_title=pr_title,
        pr_body=pr_body,
        changed_files=changed_files_data,
        unified_diff=diff_content,
        file_contents=file_contents,
        related_tests=related_tests
    )
    
    print("Requesting test coverage analysis from LLM...")
    try:
        llm_response = provider.generate_response(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        sys.exit(1)
        
    formatted_report = format_report(llm_response)
    
    # 5. Output response or post to GitHub comment
    if local_mode:
        print("\n=== GENERATED REPORT (LOCAL MODE) ===")
        print(formatted_report)
        print("======================================\n")
        
        output_file = os.environ.get("LOCAL_OUTPUT_PATH")
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(formatted_report)
            print(f"Report written to local file: {output_file}")
    else:
        try:
            print("Fetching existing PR comments...")
            comments = gh_client.get_pr_comments(pr_number)
            existing_comment = None
            for c in comments:
                if is_bot_comment(c.get("body", "")):
                    existing_comment = c
                    break
                    
            if existing_comment:
                print(f"Updating existing comment (ID: {existing_comment['id']})...")
                gh_client.update_comment(existing_comment["id"], formatted_report)
            else:
                print("Creating new PR comment...")
                gh_client.create_comment(pr_number, formatted_report)
            print("Review comment posted successfully!")
        except Exception as e:
            print(f"Error posting/updating comment on GitHub: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
