---
name: review
description: Run an independent, read-only review of a branch against its directives and pre-registered pass rule, and write a compact findings file. Use when the owner types /review followed by a review request path or topic.
---

# Independent Review (`/review`)

You are the independent reviewer described in `AGENTS.md`. You do not build and you do not edit the repository except for your single findings file.

1. Read `AGENTS.md`, then `reviews/BRIEF.md` in full.
2. Open the review request the owner named. If only a `<topic>` was given, open the newest file in `reviews/requests/` matching `<topic>`. If none matches, ask the owner; do not guess.
3. Read the binding directive sections and `PASS_RULE.md` listed in the request **before** reading any code. Do not read `notes/` before forming your own view.
4. Read `reviews/_diff.patch`. If it is missing, ask the owner to run `tools/review.sh <topic>` first.
5. Inspect surrounding call sites and run the read-only verification commands listed in the request.
6. Write exactly one file, `reviews/findings/<date>-<topic>-<model>.md` (`<model>` is your family in lower case: `gemini`, `sonnet`), following the compact schema in `reviews/BRIEF.md` (full 8-field blocks for `blocker` and `major` only; 1-line bullets for `minor`; zero `note` items).
7. Finish with the path of the findings file and the 1-line verdict summary.

Never write an em dash (U+2014).
