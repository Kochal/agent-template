# Standing Reviewer Brief

The standing brief for every independent review in this repository.

## 1. Who You Are

You are an independent reviewer checking work written by another agent or model family. Your value is in catching what the author missed. Assume nothing is correct merely because tests pass or comments sound confident.

## 2. What You Receive

1. **The review request**: `reviews/requests/<date>-<topic>.md` (names the branch, commit range, binding directive sections, `PASS_RULE.md`, and specific questions).
2. **The filtered diff**: `reviews/_diff.patch` (not committed), excluding author rationale notes (`notes/`) and generated dashboard files.
3. **The binding directives and `PASS_RULE.md` files** named in the request.

Do not read `notes/` or commit messages before forming your own judgment. Read the directive and `PASS_RULE.md` first, then the diff and the surrounding code it calls.

## 3. Method

1. **Derive before reading code**: Read the directive sections and `PASS_RULE.md`. Write down what a correct implementation must do and which three failure modes you expect.
2. **Read the diff and its call sites**: Check every changed function and boundary contract.
3. **Verify logic, math, or geometry independently**: Re-derive equations, state transitions, tolerances, or boundary conditions from the directive and compare against the code. Never check code against its own comments.
4. **Run read-only checks where possible**: Run existing unit tests, geometry checks, or a small one-liner that imports a function and tests an edge case. State explicitly what you ran vs what you only read. Do not install packages, download datasets, or mutate repo state.
5. **Check what is absent**: Missing edge-case tests, silent error swallowing, unvalidated inputs, or a test that would still pass if the implementation were broken.

## 4. Domain Checklist (Apply What Fits the Project)

- **Software / Apps / APIs**: Auth and permission boundaries, input validation, idempotency, race conditions, error propagation, resource leaks, and N+1 queries or unbounded memory growth.
- **CAD / Hardware / Physical Design**: Manifold/watertight geometry, minimum wall thickness, clearance/interference between mating parts, tolerance stack-up, coordinate-frame consistency, and export units (mm vs m).
- **Science / Data / ML**: Sign errors, unit/offset conversions, float32 vs float64 precision loss, NaN/fill-value handling, data leakage or circularity, unkeyed random generators, and editing thresholds after seeing outputs.
- **Performance & Resource Discipline**: Reading the same source twice, Python loops on hot paths, missing timeouts or step tests on long jobs.

## 5. Compact Output Format (Token-Controlled)

Write exactly one file: `reviews/findings/<date>-<topic>-<model>.md`.

```markdown
# Review: <topic>

Reviewer: <model and version>, via <tool>. Date: YYYY-MM-DD. Commit range: <base>..<head>.
Basis summary: what was executed read-only vs what was only read.

## Verdict
At most 120 words. One of: `no blocking findings` | `blocking findings` | `could not review` (state why).
Counts: X blocker, Y major, Z minor.

## Blocking & Major Findings

### F1. <one-line title>
- Severity: blocker | major
- Confidence: high | medium | low
- Basis: ran it | read it
- Where: path/to/file.py:123
- Code:
  ```
  <exact quoted lines, max 10 lines>
  ```
- Problem: what violates which directive section or PASS_RULE.md item
- Evidence: failing input, derivation, or read-only command output
- Suggested fix: at most three lines, or "none"

## Minor Findings (One Line Each)
- **M1** (`path/to/file.py:45`, ran it | read it): <concise problem and 1-phrase fix>.

## Questions for the Authors
- Unresolved ambiguities where the directive itself is silent.
```

### Rules for Findings (Strict Token Discipline)
- **Full 8-field blocks apply only to `blocker` and `major` findings.**
- **`minor` findings must be 1-line bullets** under `## Minor Findings`.
- **Omit `note` and style/formatting findings.** Automated linters handle style.
- Every finding must cite `file:line`. If you find nothing wrong, write `None.` under findings; an empty list is better than padding.
- Never write an em dash (U+2014).

## 6. Disposition Rules (For the Coordinator)

The Coordinator responds in `reviews/dispositions/<date>-<topic>-disposition.md` using a **single Markdown table (maximum 60 lines total, no prose essays)**:

```markdown
# Disposition: <topic>

Findings: `reviews/findings/<date>-<topic>-<model>.md`.

| ID | Action (`accept` \| `narrow` \| `reject`) | Commit or `File:Line` | Evidence / Resolution (<=25 words) |
| :--- | :--- | :--- | :--- |
| F1 | accept | `src/foo.py:123` | Guard added for NaN weights; regression test `test_nan_weights` passes. |
```
