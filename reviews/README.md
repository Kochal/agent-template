# Reviews

Independent reviews of work packages against active directives and pre-registered `PASS_RULE.md` checks.

| Path | Purpose | Written by |
| :--- | :--- | :--- |
| `BRIEF.md` | Standing instructions and token-controlled output schema | Template / Coordinator |
| `requests/<date>-<topic>.md` | Review scope, binding directives, `PASS_RULE.md`, and questions | Coordinator |
| `findings/<date>-<topic>-<model>.md` | Independent review findings (`blocker`/`major` blocks + 1-line `minor` bullets) | Reviewer (`Gemini 4 Argon High` or internal `Sonnet` reviewer) |
| `dispositions/<date>-<topic>-disposition.md` | Compact table (<=60 lines) resolving every finding (`accept`, `narrow`, `reject`) | Coordinator |
| `_diff.patch` | Filtered diff under review (excludes `notes/`, `dashboard/`, `99-status.md`, lockfiles); gitignored | `tools/review.sh` |
