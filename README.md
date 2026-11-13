# `<PROJECT_NAME>`

`<One-paragraph summary of what the project builds, who it serves, and what its core design or architecture is.>`

- **Entry point for agents**: [`AGENTS.md`](AGENTS.md) (imported natively by [`CLAUDE.md`](CLAUDE.md) via `@AGENTS.md`).
- **Active specifications**: Numbered directives at the repo root (`00-overview.md` to `NN-<topic>.md`, scaled to the project's scope).
- **Live project state & decisions**: [`dashboard/index.html`](dashboard/index.html) and [`99-status.md`](99-status.md), both built deterministically from [`dashboard/register.toml`](dashboard/register.toml).
- **Design rationale & research**: [`notes/index.md`](notes/index.md).
- **Multi-agent strategies & token playbook**: [`docs/agentic-strategies.md`](docs/agentic-strategies.md) (on-demand reference for 13 agentic setups and empirical token controls; zero boot-context cost).

---

## Repository Layout

| Path | Purpose | Edit Rule |
| :--- | :--- | :--- |
| `docs/source/` | Original brief, PRD, or specification document(s) | **Never edited.** Kept as historical baseline. |
| `docs/agentic-strategies.md` | Catalog of 13 multi-agent setups (Map-Reduce worktrees, Best-of-N, MCTS, AlphaEvolve, MoA, Red/Blue) and empirical token rules | On-demand reference; kept outside `AGENTS.md` so boot context stays slim. |
| `00-*.md` .. `NN-*.md` | Active directives (*what is decided now*), one topic per file (~90 to 220 lines). Each ends with `## Decided against` and `## Open` | Updated in the same commit whenever a rule or decision changes. |
| `dashboard/register.toml` | Single source of truth for decisions (`D-xxx`), open questions (`Q-xxx`), rejected options, completed work, work packages (`WP-xx`), gates (`G0..Gn`), and spend | Update via `python3 tools/build_dashboard.py` CLI subcommands or tail edits, then rebuild. |
| `dashboard/index.html`, `99-status.md` | Generated project dashboard and status summary | **Generated files.** Do not hand-edit and never read into agent context. |
| `notes/<area>/` | Dated rationale notes, spike findings, benchmarks, and contracts | Add new notes as `YYYY-MM-DD-<slug>.md` and link in `notes/index/<area>.md`. |
| `notes/briefs/` | Self-contained decision briefs for open owner questions (`Q-xxx`) | Committed in git so every `Q-xxx` has a permanent, offline-readable record. |
| `experiments/<id>/` | Pre-registered acceptance checks: feature walkthroughs, pipeline cross-checks, benchmarks, design verifications. Templates in `experiments/_template/` | Commit `PASS_RULE.md` *before* running; `RESULT.md` records its blob SHA (enforced by `tools/check.sh`). |
| `reviews/` | Cross-model and internal independent reviews (`BRIEF.md`, `requests/`, `findings/`, `dispositions/`) | Reviewers write only to `reviews/findings/`. Builders write compact table dispositions (<=60 lines). |
| `src/` (or `cad/`, `app/`), `tests/` | Project source files, models, and automated test/verification suite | Automated tests strip real credentials from the environment. |
| `.claude/agents/` | `registrar.md` (Phase 2 bookkeeping), `reviewer.md` (Tier 2 diff review), `acceptance.md` (walkthrough or pipeline cross-check). All pinned to `model: sonnet` | Spawned by the Coordinator; pass `model: "opus"` for Tier 3 scientific cross-checks. |
| `.claude/settings.json` | Shared Claude Code permissions (denies reading `.env*` and `secrets/`) | Personal overrides go in the gitignored `.claude/settings.local.json`. |
| `tools/` | `check.sh`, `check_text.py`, `build_dashboard.py`, `review.sh`, `claude_tokens.py`, `hooks/pre-push` | Run `tools/check.sh` before every push; run `python3 tools/claude_tokens.py --days 3` to audit token/USD spend. |

---

## Model Routing & Token Discipline

| Role | Model Tier | Why |
| :--- | :--- | :--- |
| **Coordinator Phase 1 (Architecture & Judgment)** | **Claude `Opus` / `Fable`** (or **`Gemini 4 Argon High`**) | High-reasoning decomposition of `docs/source/` into contracts, directives, `PASS_RULE.md` checks, review dispositions, and Decision Briefs. |
| **Coordinator Phase 2 (Bookkeeping & Integration)** | **Claude `Sonnet`** (auto-delegated via `.claude/agents/registrar.md`, or owner `/model sonnet` / resumed `Sonnet` session) | Updating `register.toml`, updating `notes/index/`, running `tools/check.sh`, and `git merge --ff-only`. Because all state is on disk, a separate `Sonnet` session or subagent can resume Phase 2 with zero `Opus` turns. |
| **Core Implementation Lanes (Tier 3)** | **Claude `Opus` / `Fable`** | Algorithms, numerical kernels, intricate CAD geometry, security boundaries, and complex state machines. |
| **Cross-Model Independent Review (`/review`)** | **Google Antigravity (`Gemini 4 Argon High`)** | Genuine cross-family verification of `WP-S0`, Tier 2/3 modules, and gate freezes on a separate subscription. Kimi is excluded on private repos. |

---

## Adapting the Structure Across Project Types

The same five primitives (**Directives**, **Register/Dashboard**, **Notes**, **Pre-registered Pass Rules**, and **Independent Reviews**) adapt to any technical project:

| Concept | App or Software Tool | CAD / Hardware / Physical Design | Science / Data / ML Pipeline |
| :--- | :--- | :--- | :--- |
| **Directives (`00..NN`)** | `00-overview`, `01-licences`, `02-architecture`, `03-data-model`, `04-api-contracts`, `05-ui-ux`, `06-security`, `07-deployment`, `08-roadmap`, `09-workflow` | `00-overview`, `01-envelope-interfaces`, `02-materials-bom`, `03-manufacturing-dfm`, `04-tolerances-fits`, `05-assemblies`, `06-testing-inspection`, `07-roadmap`, `08-workflow` | `00-overview`, `01-licences`, `02-data-sources`, `03-infrastructure`, `04-stack`, `05-compute-efficiency`, `06..NN-methods`, `NN-validation`, `NN-workflow` |
| **Pass Rules (`experiments/<id>/PASS_RULE.md`)** | Latency (`p95 < 100 ms`), bundle size budget, accessibility score, zero-regression E2E user flows | Watertight/manifold mesh check, minimum wall thickness (`>= 1.5 mm`), zero part interference, mass/CoG bounds, FEA safety factor | Known-answer oracle match, synthetic calibration coverage, placebo false-positive rate, historical backtests |
| **Independent Oracle** | Contract test suite or reference state-machine model written separately from the UI/backend | Independent geometry validator script (bounding box, clearance, volume, STEP/STL export check) | Second implementation (`fit_b`) or plain unoptimised reference kernel vs fast kernel |
| **Owner Questions (`Q-xxx`)** | User-facing behavior, feature trade-offs, pricing/infra tiers, third-party integrations | Form factor, connector/fastener choices, material trade-offs, tolerance vs manufacturing cost | Methodology choices, region/index definitions, dataset selection, acceptance thresholds |

---

## How to Bootstrap a New Project (`WP-S0` Startup Guide)

### Step 1: Copy this template directory and drop in your source brief
1. Copy the whole `project-template/` directory (including the dot folders `.agents/` and `.claude/`) into your new repository root, then `git init`.
2. Enable the pre-push check once per clone: `git config core.hooksPath tools/hooks`.
3. In `dashboard/register.toml`, replace `<PROJECT_NAME>` and the `YYYY-MM-DD` placeholders, then run `python3 tools/build_dashboard.py`.
4. Place your initial project brief, PRD, or specification in `docs/source/YYYY-MM-DD-plan-v1.0.md`.

### Step 2: Run the Day-0 Coordinator Prompt (on `Opus` / `Fable` or `Gemini 4 Argon High`)
Start your Coordinator agent with:

```text
Read AGENTS.md and docs/source/<your-plan-file>.md.
Execute WP-S0 (Repository Setup):
1. Write a setup contract note in notes/ops/YYYY-MM-DD-repo-setup-contract.md mapping sections of the source plan to numbered directives (00-overview.md through NN-<topic>.md, sized at roughly 90 to 220 lines per file), gates (G0..Gn), and work packages (WP-xx). Choose the directive set that fits this project type (app/tool, CAD/hardware, or data/science).
2. Spawn parallel directive-writer subagents (`Opus` for core architecture/methods/validation, `Sonnet` for lighter UI/deployment/ops) to turn the source plan into the numbered directives under the rule "add nothing the plan does not state". Every place where the plan is silent or ambiguous becomes an entry under `## Open` tagged with who settles it ([Q-xxx] for owner decisions, [WP-xx] for empirical measurements or prototypes). Every option the plan rejects goes into `## Decided against`. Each subagent returns a 1-line-per-item summary of decisions, rejected options, and open questions.
3. Populate dashboard/register.toml with the initial locked decisions (D-xxx), rejected options, gates, work packages, and the first batch of open owner questions (Q-xxx), with a committed brief in notes/briefs/YYYY-MM-DD-<slug>.md for the first decision batch.
4. Create the initial pre-registered PASS_RULE.md files under experiments/ (from experiments/_template/) for the project's acceptance gates: walkthroughs for user-facing features, cross-checks for scientific results. List any unfixed thresholds under Open.
5. Scaffold the project workspace, wire up project-specific checks in tools/check.sh, and run tools/check.sh until all checks pass.
```

### Step 3: Optional Day-0 Plan Gap Audit (Google Antigravity `Gemini 4 Argon High`)
Before closing Gate `G0`, run an independent cross-model check in Antigravity to verify that no constraint or ambiguity in `docs/source/` was missed during `WP-S0`.

---

## Day-to-Day Workflow

### 1. Running checks (before every commit/push)
```bash
tools/check.sh
```
This runs:
- `python3 tools/check_text.py`: UTF-8, no em dash, notes index links and orphans, `## Decided against` / `## Open` in every directive, and pass-rule integrity (each `RESULT.md` must name the blob SHA of the current `PASS_RULE.md`).
- `python3 tools/build_dashboard.py --check`: register invariants (ids unique; packages point at real gates; work points at real packages and files; date sync) and freshness of `dashboard/index.html` and `99-status.md`.
- The project's own build, lint, type, geometry, or test suite.

### 2. Reading and updating `dashboard/register.toml` without opening it
Every edit is parsed and validated before it is written, so a bad edit leaves the file untouched. `key=value` stores a string; `key:=json` stores a number, list, or inline table.
```bash
# Inspect
python3 tools/build_dashboard.py list question --status open
python3 tools/build_dashboard.py show D-004

# Add any entry kind: decision, question, package, gate, rejected, work, spend
python3 tools/build_dashboard.py add question id=Q-001 opened=2026-11-12 title="Export format" \
  needed_by=2026-11-20 recommendation="CSV" default="CSV" status=open brief=notes/briefs/2026-11-12-export.md
python3 tools/build_dashboard.py add decision id=D-001 date=2026-11-12 by=owner area=data \
  title="Export format" decided="CSV" status=specified implementation="src/export.py" \
  rejected:='[{"option": "XLSX", "why": "Extra dependency"}]'

# Change fields
python3 tools/build_dashboard.py set G0 status=passed
python3 tools/build_dashboard.py set WP-03 status=done

# Shortcuts. Logging work moves an open package to "in progress", never to "done".
python3 tools/build_dashboard.py add-work --date 2026-11-12 --package WP-S0 \
  --title "Directives drafted" --detail "00 to 09 written." --ref 00-overview.md
python3 tools/build_dashboard.py answer-question Q-001 --date 2026-11-12 --answer "Option A selected."
python3 tools/build_dashboard.py add-spend --date 2026-11-12 --item "Step test cx23" --eur 0.01
```

### 3. Answering Owner Questions (`Q-xxx`)
1. Open `dashboard/index.html` in a browser and review the **Needs your decision** section (and linked briefs in `notes/briefs/`).
2. Give your answers in chat. The coordinator records your words verbatim in `notes/plan/YYYY-MM-DD-owner-decisions-verbatim.md`, updates the affected directives (`00..NN`), marks `Q-xxx` as `answered` and logs `D-xxx` in `dashboard/register.toml`, and rebuilds the dashboard.

### 4. Running a Tiered Independent Review
From a local checkout in Git Bash:
```bash
tools/review.sh <topic> [branch]
```
`tools/review.sh` writes a clean `reviews/_diff.patch` (stripping `notes/`, `reviews/`, `dashboard/`, `99-status.md`, and lockfiles so author rationale and earlier dispositions never reach the reviewer and generated files never bloat context).
- Tier 2 inside Claude Code: spawn `.claude/agents/reviewer.md`, which writes `reviews/findings/<date>-<topic>-sonnet.md`.
- Tier 3 in Google Antigravity (`Gemini 4 Argon High`): run `/review <topic>`, which writes `reviews/findings/<date>-<topic>-gemini.md` (full blocks for `blocker`/`major` only; 1-line bullets for `minor`).
- The Coordinator then writes `reviews/dispositions/<date>-<topic>-disposition.md` as a compact Markdown table (max 60 lines) recording `accept`, `narrow`, or `reject` with file-and-line evidence before merging.

### 5. Closing a Feature or Gate with a Bundled Spec QA Run
A review reads the diff. The acceptance run uses the result: an agent that built none of the bundle clicks through the feature, or runs the pipeline and cross-checks its output, against the spec, and records each step. It runs once per feature or gate, not once per package, so its cost is paid once for several packages.
1. **Register the bundle.** When the Coordinator plans a feature or gate, it copies `experiments/_template/PASS_RULE.md` to `experiments/<id>/`, lists the packages it covers, and writes the steps from the directive sections (the spec), not from the code. Keep the walkthrough table (features) or the cross-check table (science/data), fix the thresholds, and commit before building.
2. **Build and close packages as usual.** Each package closes on its own tier checks. Small changes with no bundle of their own join the next one.
3. **Run once the bundle is built.** Spawn `.claude/agents/acceptance.md` with the experiment id (add `model: "opus"` for Tier 3 scientific checks). It drives the real UI or pipeline, saves evidence to `experiments/<id>/evidence/`, and writes `RESULT.md` with `k of n rules pass`.
4. **Close the feature or gate at `n of n`.** A failing step reopens the package responsible (`set WP-xx status="in progress"`); after the fix, rerun the same `PASS_RULE.md`. Any step the owner waives is logged as a decision.
5. **Fix rules openly.** If a step itself proves wrong, copy the folder to `<id>-v2` and fix it there. `tools/check.sh` fails if a `PASS_RULE.md` changes after its `RESULT.md` exists.
