# Zetestic

A GitHub Action and Python tool that automatically reviews Pull Request (PR) diffs to determine if the changes have adequate test coverage. 

It analyzes the code diff, locates related existing tests, identifies changed/added behavior, determines coverage status, and suggests concrete tests to write. It posts a formatted report as a PR comment and automatically updates its previous comment on subsequent commits to avoid spamming the PR conversation.

> [!IMPORTANT]
> Note: Requires your own LLM API key (Google Gemini, Anthropic Claude, or OpenAI GPT).
> Requires Python 3.8+ for local runs (Python 3.11 is used in CI).

## Features

- **Behavior-Focused:** Does not review code style, performance, or unrelated issues. Focuses purely on: *"Did this PR add or update enough tests for the behavior it changed?"*
- **Structured Test Obligations:** Extracts a typed list of `TestObligation` objects from the diff — each with an id, title, symbols, behavioral search terms, expected behavior, and obligation type. These become intermediate objects the pipeline can inspect and act on.
- **Code-Based Coverage Search:** Searches the existing test files for each obligation using two strategies: symbol matching (exact function/class names) and behavioral keyword matching (`search_terms`). Each obligation is assigned a `covered`, `partial`, or `missing` status before the final report is generated.
- **Deleted File Detection:** Deleted source files are explicitly surfaced in the extraction prompt so deletion-triggered regression obligations (e.g. tests that reference removed code) can be flagged.
- **Test-Only PR Detection:** When a PR only changes test files, obligation extraction is skipped entirely to avoid wasted API calls and phantom obligations derived from test code.
- **Smart Test Finding:** Locates existing test files using structural matching and naming convention similarity heuristics.
- **De-duplication:** Automatically finds and updates its previous review comments instead of flooding the PR with new comment threads.
- **Multi-Provider Support:** Supports Anthropic (Claude), Google Gemini, and OpenAI out of the box via lightweight direct HTTP APIs.

## GitHub Setup (Actions)

To use the agent in any repository, add a workflow file at `.github/workflows/test-coverage-agent.yml` with the following content:

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
          llm_api_key: ${{ secrets.YOUR_API_KEY_SECRET }}  # Change YOUR_API_KEY_SECRET to your own LLM API key.
          llm_provider: anthropic  # Options: anthropic, gemini, openai.
          llm_model: claude-opus-4-5  # Optional: pin a specific model.
```

Then add your LLM API key to the repository's **Settings → Secrets and variables → Actions**:

| Provider | Secret name | `llm_provider` value |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY` | `gemini` |
| Anthropic Claude | `ANTHROPIC_API_KEY` | `anthropic` |
| OpenAI GPT | `OPENAI_API_KEY` | `openai` |

That's all. No Python files, no pip installs — the action handles everything internally.

---
