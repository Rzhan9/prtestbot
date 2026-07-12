# GitHub PR Test Coverage Review Agent

A GitHub Action and Python tool that automatically reviews Pull Request (PR) diffs to determine if the changes have adequate test coverage. 

It analyzes the code diff, locates related existing tests, identifies changed/added behavior, determines coverage status, and suggests concrete tests to write. It posts a formatted report as a PR comment and automatically updates its previous comment on subsequent commits to avoid spamming the PR conversation.

## Features

- **Behavior-Focused:** Does not review code style, performance, or unrelated issues. Focuses purely on: *"Did this PR add or update enough tests for the behavior it changed?"*
- **Smart Test Finding:** Locates existing test files using structural matching and naming convention similarity heuristics.
- **De-duplication:** Automatically finds and updates its previous review comments instead of flooding the PR with new comment threads.
- **Multi-Provider Support:** Supports Anthropic (Claude), Google Gemini, and OpenAI out of the box via lightweight direct HTTP APIs.
- **Local Dry-Runs:** Run the analysis locally against any repository diff without requiring a GitHub Action environment.

---

## Directory Structure

```text
test-coverage-agent/
  src/
    test_coverage_agent/
      __init__.py
      main.py
      github_client.py
      repo_analyzer.py
      diff_parser.py
      test_finder.py
      llm_provider.py
      prompt_builder.py
      report_formatter.py
  tests/
    test_diff_parser.py
    test_test_finder.py
    test_report_formatter.py
  README.md
  requirements.txt
  .env.example
```

---

## GitHub Setup (Actions)

To use the agent in any repository, add a workflow file at `.github/workflows/test-coverage.yml` with the following content:

```yaml
name: PR Test Coverage Review

on:
  pull_request:
    types: [opened, reopened, synchronize, ready_for_review]

jobs:
  review:
    runs-on: ubuntu-latest
    if: github.event.pull_request.draft == false
    permissions:
      contents: read
      pull-requests: write
      issues: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: Rzhan9/prtestbot@main
        with:
          llm_api_key: ${{ secrets.YOUR_API_KEY_SECRET }}
          llm_provider: gemini  # or: anthropic, openai
```

Then add your LLM API key to the repository's **Settings → Secrets and variables → Actions**:

| Provider | Secret name | `llm_provider` value |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY` | `gemini` |
| Anthropic Claude | `ANTHROPIC_API_KEY` | `anthropic` |
| OpenAI GPT | `OPENAI_API_KEY` | `openai` |

That's all. No Python files, no pip installs — the action handles everything internally.

---


