# Pass rule: <id>

Bundled spec QA for: `<feature name>` or gate `Gn`. Covers packages: WP-xx, WP-yy, WP-zz.
Spec: `NN-<topic>.md` (section titles). Written YYYY-MM-DD, before anything was built or run.
Executor: an agent that built none of the covered packages (`.claude/agents/acceptance.md`).

Write each step from the spec, not from the code. Use the Spec column to point at the section a step checks, and the Package column to say which package a failure reopens.

Never edit this file after a `RESULT.md` exists; `tools/check.sh` fails if you do. If a rule proves wrong, copy the folder to `<id>-v2`, fix it there, and state why in its first line.

## Setup

- Commit under test: `<sha or branch>`
- Start or run command: `<e.g. npm run dev | uv run pipeline --config configs/x.toml>`
- Fixtures and data: `<path, version, sha256>`

## Rules

One observable check per row, each with a fixed threshold. Keep the shape that fits and delete the other.

### Walkthrough (app, dashboard, CLI)

| # | Action | Expected | Spec | Package |
| :--- | :--- | :--- | :--- | :--- |
| R1 | Open `/dashboard` as the test user | Page renders within 3 s; no console errors | `05-ui-ux.md` 2 | WP-xx |
| R2 | Click "Export", choose CSV | File downloads; 12 columns in the specified order | `05-ui-ux.md` 3 | WP-yy |
| R3 | Submit the form with an empty required field | Inline error shown; nothing saved | `04-api-contracts.md` 1 | WP-zz |

### Pipeline cross-check (science, data, ML)

| # | Check | Pass if | Spec | Package |
| :--- | :--- | :--- | :--- | :--- |
| R1 | Run the pipeline on fixture `<x>` | Exits 0 within 10 min | `03-infrastructure.md` 2 | WP-xx |
| R2 | Known-answer case `<y>` | Result within `1e-6` of the reference value `<v>` | `06-methods.md` 4 | WP-yy |
| R3 | Recompute the headline number independently (`fit_b`, hand calculation, or reference script) | Relative difference below 0.5% | `NN-validation.md` 1 | WP-yy |
| R4 | Invariant (conservation, sums to 1, sign, units) | Holds for every output row | `06-methods.md` 2 | WP-zz |

## Open

- Thresholds not yet fixed, tagged `[Q-xxx]` or `[WP-xx]`.
