# AGENTS.md

Entry point for coding and design agents (Claude Code, Google Antigravity / Gemini, OpenAI Codex). `CLAUDE.md` imports this file with `@AGENTS.md`, so it sits in the prompt-cached system context. Keep it under 8 KB; playbooks live in `docs/agentic-strategies.md`.

## 1. Project, Privacy & Roles

- **Project**: `<PROJECT_NAME>`: `<one sentence: what we build and what is out of scope>`.
- **Privacy**: `PRIVATE` by default. Do not copy code, specs, or notes outside this workspace. Do not invoke Kimi on private repositories.
- **Check your role before acting**:
  - **Coordinator, Phase 1 (`Opus`/`Fable`)**: `WP-S0` decomposition, contract notes (`notes/ops/YYYY-MM-DD-<wp>-contract.md`), `PASS_RULE.md` files, review dispositions (`accept`/`narrow`/`reject`), owner Decision Briefs (`notes/briefs/`).
  - **Coordinator, Phase 2 (`Sonnet`)**: register, `notes/index/`, `tools/check.sh`, `git merge --ff-only`. Delegate in one call to `.claude/agents/registrar.md`, or hand over to a `Sonnet` session (all state is on disk).
  - **Core lanes (`Opus`/`Fable`)**: algorithms, numerical kernels, complex state or CAD geometry, security boundaries. Branch `<wp>-<topic>`.
  - **Light lanes and search (`Sonnet`)**: well-specified plumbing, CLI/UI wiring, test expansion, codebase search.
  - **Acceptance runner (`.claude/agents/acceptance.md`)**: runs a feature's or gate's bundled spec QA `PASS_RULE.md` against code it did not build and writes `RESULT.md`. Tests; never fixes.
  - **Cross-model reviewer (`Gemini 4 Argon High`, Antigravity `/review`)**: **You review; you do not build.** Write only `reviews/findings/<date>-<topic>-<model>.md`; no commits, pushes, installs, or state changes. Follow `reviews/BRIEF.md`.

## 2. Where Truth Lives & Read Discipline

Never rely on chat history. Every durable fact lives in one of five places:

| Location | Holds | Rule |
| :--- | :--- | :--- |
| `docs/source/` | Original brief / spec | Read-only archive. |
| `00-*.md` .. `NN-*.md` | **What is true now** | One topic per file (~90 to 220 lines). Update in the same commit as the decision. End with `## Decided against` and `## Open` (items tagged `[Q-xxx]` or `[WP-xx]`). |
| `dashboard/register.toml` | **Project state** | Decisions `D-xxx`, questions `Q-xxx`, rejected options, work log, packages `WP-xx`, gates `G0..Gn`, spend. Generates `dashboard/index.html` and `99-status.md`. |
| `notes/<area>/YYYY-MM-DD-<slug>.md` | **Why** | Rationale, benchmarks, spikes, briefs (`notes/briefs/`). Indexed in `notes/index/<area>.md`. |
| `experiments/<id>/` | **Acceptance** | One per feature, gate, or benchmark. `PASS_RULE.md` committed before the run; `RESULT.md` records its blob SHA, environment, per-rule evidence, and `k of n rules pass`. Templates: `experiments/_template/`. |

### Token discipline (evidence and playbook: `docs/agentic-strategies.md`)

Every request re-reads the whole context, and every subagent boots at ~75k tokens.
1. **Set `model` on every subagent call.** Omitting it inherits the parent (`Fable`/`Opus`, high effort). `sonnet` for search, UI, plumbing, re-tests, bookkeeping, walkthroughs; `opus` for core algorithms, math, architecture, Tier 3 cross-checks.
2. **Cap subagents at ~60 requests.** Split larger packages, or write a handover note to `notes/<area>/` and exit. After 15 failed turns on one fix, `git reset` to the last good commit, write a 2-line failure note, and restart fresh.
3. **Batch tool calls.** Combine checks, reads, and test runs into one command or script.
4. **Compact or rotate at 150k to 200k tokens**, and after an idle gap longer than the cache TTL (5 min for subagents; often 1 h for main sessions).
5. **Never read in full**: `docs/source/*` after `WP-S0`, `dashboard/index.html`, `99-status.md`, `dashboard/register.toml`, lock or data files. PDFs: max 5 pages per read, or extract text.
6. **Route reads**: `notes/index.md` -> one `notes/index/<area>.md` (once per session) -> the flagged note. Query and edit the register only through `tools/build_dashboard.py` (`list`, `show`, `add`, `set`).

## 3. Non-Negotiables

1. **Acceptance rules before results.** Commit `PASS_RULE.md` before running benchmarks, validations, or walkthroughs. Never edit it after a result exists; copy to `<id>-v2` instead. `tools/check.sh` fails if `PASS_RULE.md` no longer matches the blob SHA in `RESULT.md`.
2. **Independent verification.** The agent that builds a package never marks it done.
   - **Tier 1** (plumbing, formatting, CRUD): `tools/check.sh` and automated tests.
   - **Tier 2** (standard modules, API/data contracts, CAD parts): one diff review by `.claude/agents/reviewer.md` or `Gemini 4 Argon`.
   - **Tier 3** (`WP-S0` freeze, scientific kernels, security boundaries, critical geometry, gate freezes): cross-model review (`/review <topic>`) plus an independent oracle (`fit_b`, reference validator, or contract tests).
   - **Acceptance run (bundled spec QA)**: one `experiments/<id>/PASS_RULE.md` per feature or gate, not per package. Its steps come from the spec (directive sections) and cover every package in the bundle; small changes join the next bundle. Once the bundle is built, an agent that built none of it runs the steps (click-through walkthrough, or pipeline run plus independent cross-checks) and records evidence in `RESULT.md`. The feature or gate closes only at `n of n`; a failing step reopens the package responsible.
   - **Output caps**: full finding blocks only for `blocker`/`major`; `minor` as 1-line bullets; omit style notes. Dispositions: one table (`ID | Action | Commit or File:Line | <=25-word evidence`), max 60 lines.
3. **Resource discipline.** Step-test cost, runtime, or size before long builds, renders, simulations, or cloud jobs. Jobs over 10 min are resumable, log resource use, and have a timeout.
4. **Licences.** Verify licences of libraries, assets, fonts, datasets, and CAD parts at the source before adoption; record them in the licence directive.
5. **Secrets.** Never read, print, or commit credentials (`.claude/settings.json` denies `.env*`). Tests strip real credentials from the environment.

## 4. Owner vs Coordinator Decisions

- **Ask the owner** (Decision Brief) only for product behavior, UX/geometry/methodology, scope, budget or schedule, and reversals of locked decisions. Max 5 questions per brief in `notes/briefs/YYYY-MM-DD-<slug>.md`; register each `Q-xxx` with `id`, `opened`, `title`, `needed_by`, `recommendation`, `default`, `brief`, `status`. Record answers verbatim in `notes/plan/YYYY-MM-DD-owner-decisions-verbatim.md`.
- **Decide as Coordinator** (log with `by = "coordinator"`): internal engineering, refactoring, tooling, file layout, housekeeping. Never close an `## Open` product, design, or methodology item as coordinator.

## 5. Multi-Agent Coordination

The Coordinator (one per session) writes the contract note first, spawns lane writers, adjudicates reviews, and merges to `main` with `git merge --ff-only`. Lane writers work on `<wp>-<topic>`, read their contract note first, and touch only the files it names.

## 6. Style

- Short declarative sentences (fact, reason, consequence). No hype or filler.
- **Never write an em dash (U+2014)** in prose, code, comments, or commit messages.
- Quote every metric with scope, unit, and source (`k of n rules pass`, never bare "passed").

## 7. Commands (Run Before Every Push)

```bash
tools/check.sh       # text, directive sections, pass-rule SHAs, register, project tests
python3 tools/build_dashboard.py list question --status open
python3 tools/build_dashboard.py show Q-001
python3 tools/build_dashboard.py add decision id=D-001 date=YYYY-MM-DD by=owner area=scope title="..." decided="..." status=specified implementation="..."
python3 tools/build_dashboard.py set WP-S0 status=done
python3 tools/build_dashboard.py add-work --date YYYY-MM-DD --package WP-S0 --title "..." --detail "..." --ref 00-overview.md
```
