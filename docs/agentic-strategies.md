# Multi-Agent Strategies & Empirical Token Playbook

On-demand reference for the Coordinator and project owner. Kept in `docs/agentic-strategies.md` (outside `AGENTS.md`) so it adds **zero tokens** to the per-request boot context of main sessions and subagents.

---

## 1. Empirical Post-Mortems: Where Billions of Tokens Actually Go

Measurements from two production sessions built under this workflow establish what actually drives token spend and dollar cost:

| Metric | Case A: app rewrite (2 days) | Case B: science project setup (`WP-S0` + kernels) |
| :--- | :--- | :--- |
| **Total Billed Tokens** | **3.04 Billion tokens** (10,689 requests) | **1.035 Billion tokens** (58 rounds) |
| **List-Price Cost** | **~$2,216 USD** (Opus 5.5 + Fable 5.2 + Sonnet 5.5) | **$619.56 USD** ($374 Opus 5.5, $239 Fable 5.2, $4 Sonnet/Haiku) |
| **Token Split** | 98.6% cache read (3.00B), 34M cache write, 8.7M output | 94.7% cache read (980.8M), 46.3M cache write, 5.0M output |
| **Main vs. Subagents** | Main: 4% (117M tok, 249 req) / **Subagents: 96% (2.91B tok, 10,440 req across 89 agents)** | Main: 2.6M 1h-cache writes / **Subagents: 94% of cache writes (43M tok on 5-min tier across 9 agents)** |
| **Context Window Size** | Main avg 469k (peak 742k); top 20 subagents avg 260k to 440k (peak 650k) | Main grew to ~900k autocompact threshold (ended at 312k) |

### Six Structural Root Causes Identified

1. **Context Length $\times$ Request Count ($O(T \times C)$)**:
   - Every tool call (`Bash`, `Read`, `Edit`, browser click) is a separate API request that re-reads the entire conversation so far.
   - In Case A, a single subagent ran for **527 requests** at an average context of ~300k tokens = **155M tokens** for one subagent.
2. **Unpinned Subagent Model Inheritance**:
   - Spawning a subagent without an explicit `model` parameter inherits the parent session's model (`Fable 5.2` or `Opus 5.5`) and `high` effort. In Case A, 80 of 89 subagents ran on `Opus 5.5` (60) or `Fable 5.2` (20) at `high` effort.
3. **The 75k-Token Subagent Boot Tax**:
   - Median first-request context of a fresh subagent is **~75k tokens** (system prompt, `AGENTS.md`/`CLAUDE.md`, memory index, MCP server schemas, and skill listings). Every request that subagent makes re-pays that 75k base.
4. **The 1M-Window Autocompact Trap (`900k` threshold)**:
   - With a 1M context window, automatic compaction does not trigger until ~900k tokens. Allowing a session to cruise between 300k and 800k tokens multiplies every turn's cache-read bill by 4x to 8x compared to compacting at 150k.
5. **5-Minute Ephemeral Cache Expiry on Subagent Hand-Backs**:
   - In Case B, a 45-minute wall-clock gap before the final round expired the 5-minute cache tier, causing 3.0M tokens of fresh cache writes ($15.96 for a single round).
6. **Unbounded Single Reads (PDFs & Repeated Index Reads)**:
   - Reading 4 scratchpad PDFs in full added 600k, 450k, 157k, and 109k tokens into subagent contexts, inflating every subsequent turn in those agents. One area index file was read 21 separate times (~208k tokens).

---

## 2. Mandatory Token-Control Rules (Enforced in `AGENTS.md`)

| Rule | Target Threshold | Why It Works |
| :--- | :--- | :--- |
| **1. Hard Subagent Request Budget** | **Max 60 requests (turns) per subagent** | Prevents 200 to 500-turn contexts. If a task needs more than ~50 tool calls, the subagent writes a checkpoint note to `notes/<area>/` and exits so a fresh subagent starts at 75k instead of 450k. |
| **2. Mandatory Explicit `model` on Subagents** | Always pass `model: "sonnet"` or `model: "opus"` | Prevents accidental inheritance of `Fable 5.2` or `Opus 5.5` on UI, test, search, or mechanical fix subagents. |
| **3. Batch Tool Calls (No Micro-Stepping)** | Combine checks/edits into 1 command or script | In Case A, 6,803 individual `Bash` calls drove the request count. Running `tools/check.sh` or a 10-line Python verification script in 1 call replaces 15 separate shell requests. |
| **4. Early Compaction / Handover** | **`/compact` or new session at 150k to 200k tokens** | Never let a main session drift toward the 900k autocompact mark. |
| **5. Page-Range Cap on PDFs & Large Files** | Max 5 pages per `Read` on PDFs; `offset`/`limit` on large text | Prevents a single 500k-token PDF read from taxing the next 100 turns. |
| **6. Slim Boot Context** | Keep `AGENTS.md` < 8 KB; keep strategies/skills on-demand | Directly reduces the 75k per-subagent startup footprint. |

---

## 3. Catalog of Multi-Agent Setups & When to Deploy Each

Choose the lightest topology that matches the coupling and verification risk of your work package:

### A. Core Template Topologies (Default Daily Workflow)

1. **Setup 01: Prompt-Cached Router + On-Demand Skills**
   - *Mechanism*: Small `@AGENTS.md` prefix (< 8 KB, about 2k tokens) + `notes/index.md` router + on-demand `00..NN` directives and `.agents/skills/`.
   - *Use when*: Always active as the base layer.
2. **Setup 02: Two-Phase Coordinator (`Opus`/`Fable` Judgment -> `Sonnet` Registrar)**
   - *Mechanism*: Coordinator writes contract note (`notes/ops/YYYY-MM-DD-<wp>-contract.md`) and `PASS_RULE.md` on `Opus`/`Fable`, spawns capped lane subagents (<=60 turns), adjudicates reviews, and delegates mechanical bookkeeping (`register.toml` CLI, `notes/index/`, `check.sh`, `git merge --ff-only`) to `.claude/agents/registrar.md` (`model: sonnet`).
   - *Use when*: Standard feature, science, or CAD work packages.
3. **Setup 03: Cross-Family Blind Review Packet (`tools/review.sh` + `Gemini 4 Argon High`)**
   - *Mechanism*: Strips `notes/`, `dashboard/`, `99-status.md`, and lockfiles from `_diff.patch`. Reviewer in Google Antigravity derives expected behavior from the directive and `PASS_RULE.md` before reading the diff.
   - *Use when*: Tier 2 and Tier 3 packages, `WP-S0` setup audit, and gate freezes (`G0..Gn`).
4. **Setup 04: Dual-Implementation / Independent Oracle (`fit_a` vs `fit_b`)**
   - *Mechanism*: Agent A writes the fast production kernel or CAD model (`fit_a`); an isolated Agent B writes a plain reference implementation or geometry validator (`fit_b`) from the directive alone with zero shared code.
   - *Use when*: Tier 3 mathematical/statistical kernels, financial/billing logic, or safety-critical CAD assemblies.
5. **Setup 05: Git-Worktree Sharded Swarm (Map-Reduce Lanes)**
   - *Mechanism*: Horizontal data parallelism. Coordinator freezes shared types in a contract note (**Map**), spawns $N$ homogeneous `Sonnet` workers in isolated `git worktree` checkouts (`<wp>-slice-1 .. N`) with zero inter-worker chat, and merges slices that pass `tools/check.sh` (**Reduce**).
   - *Use when*: 4 to 15 completely disjoint file targets (e.g., dataset readers, API endpoints, UI views, or independent CAD parts).
6. **Setup 06: Pre-Registered Harness Loop & Step-Tested Async Jobs**
   - *Mechanism*: Hash-locked `PASS_RULE.md` prevents test weakening; 1-unit step tests size cloud jobs (>10 min) that run detached with `sha256` unit checkpoints and self-deleting systemd watchdogs.
   - *Use when*: Performance tuning, compression benchmarks, and long-running compute/renders.
   - *Bundled spec QA* uses the same `PASS_RULE.md` / `RESULT.md` pair, one per feature or gate rather than per package, so one subagent run covers several packages: `.claude/agents/acceptance.md` clicks through the feature or reruns the pipeline with independent cross-checks against the spec and records per-rule evidence. `tools/check.sh` rejects a `PASS_RULE.md` edited after its result.

### B. Specialized Multi-Agent Strategies (Deploy Selectively)

7. **Setup 07: Best-of-$N$ Competitive Tournament (Parallel Speculative Sampling)**
   - *Mechanism*: Assign $N$ isolated worktree agents (e.g., 2 `Opus` + 1 `Gemini 4 Argon`) the **exact same hard problem** simultaneously. Run all $N$ patches against the deterministic test/benchmark harness and promote the cleanest passing solution.
   - *Cost & Benefit*: $N\times$ single-task cost, but breaks "trajectory lock-in" on high-risk bottlenecks where a single agent gets stuck in a 200-turn debugging loop (which costs more than 3 short parallel attempts of 30 turns each).
8. **Setup 08: Monte Carlo Tree Search (MCTS) / Hard Git-Reset Backtracking (*SWE-Search*)**
   - *Mechanism*: Treat git commits as search-tree nodes. If a subagent's approach degrades tests or stalls after 15 to 20 turns, **do not let it "fix forward" in a polluted context**. Record a 2-line failure note ("Approach X failed because Y"), `git reset --hard` to the parent SHA, and spawn a fresh subagent that reads the failure note and takes a different branch.
   - *Cost & Benefit*: Avoids the 300-turn "sunk-cost spiral" seen in three Case A fix agents.
9. **Setup 09: Evolutionary Island Swarms (*AlphaEvolve* / *FunSearch* Pattern)**
   - *Mechanism*: Maintain a lightweight JSON/SQLite table of working code variants scored by an objective numerical fitness metric (throughput, memory, compression ratio, CAD mass). A script samples pairs of top-scoring programs and calls a fast stateless model (`Sonnet` or `Gemini Flash`) to mutate or combine them over 50 to 200 short single-turn generations.
   - *Cost & Benefit*: Because each mutation is a **1-turn stateless call** (~4k tokens, not a 200-turn agent session), 100 evolutionary generations cost less than a single long subagent while discovering non-obvious algorithmic optimizations.
10. **Setup 10: Blackboard / Shared Message-Board Swarm (Peer-to-Peer Collaboration)**
    - *Mechanism*: 2 to 4 specialist peers + 1 verifier share a live message board (e.g., Antigravity native `swarm`), waking on `@mentions` to negotiate coupled interfaces in real time.
    - *Cost & Benefit*: High flexibility for tightly coupled client/server or multi-module co-design, but high token cost ($O(M \times \text{posts})$). Cap board posts to concise contract changes and completion notices.
11. **Setup 11: Mixture-of-Agents (MoA) Proposer-Aggregator Ensemble**
    - *Mechanism*: Send a critical architectural or mathematical specification prompt independently to `Claude Opus/Fable` and `Gemini 4 Argon High` (Layer 1). Feed both drafts into an Aggregator turn (Layer 2) to diff their assumptions and synthesize the final directive.
    - *Cost & Benefit*: Only 2 to 3 turns total. Ideal for `WP-S0` setup and Gate `G1` methodology freezes.
12. **Setup 12: Red-Team / Blue-Team Adversarial Co-Evolution (Builder vs. Breaker)**
    - *Mechanism*: Blue Agent (`Opus`/`Sonnet`) writes the module; Red Agent (`Gemini 4 Argon` or isolated `Sonnet`) is forbidden from editing `src/` and is tasked strictly with writing Hypothesis property tests or malformed inputs that crash Blue's code. Every crash becomes a permanent regression test.
    - *Cost & Benefit*: ~2x module cost; eliminates edge-case crashes in parsers, numerical kernels, and auth boundaries.
13. **Setup 13: Deterministic Python State-Graph Pipelines (*LangGraph* / Code-Driven DAGs)**
    - *Mechanism*: For any operational task executed more than 20 times, replace the LLM Coordinator with a deterministic Python state machine that invokes small, stateless, schema-validated LLM prompts at specific graph nodes.
    - *Cost & Benefit*: Removes cumulative session history from every call; the saving grows with the number of turns an LLM coordinator would otherwise take. Measure it with `tools/claude_tokens.py` before and after.
