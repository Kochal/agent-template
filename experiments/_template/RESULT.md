# Result: <id>

PASS_RULE.md blob: `<output of git hash-object experiments/<id>/PASS_RULE.md>`
Run YYYY-MM-DD by <model>, via <tool>. Commit under test: `<sha>`. Environment: <OS, runtime, key versions>.
Score: k of n rules pass.

| # | Result | Observed | Evidence | Reopens |
| :--- | :--- | :--- | :--- | :--- |
| R1 | pass | Rendered in 1.2 s; 0 console errors | `evidence/r1.png` | |
| R2 | fail | CSV has 11 columns; `region` missing | `evidence/r2.csv` | WP-yy |
| R3 | blocked | Rule names no test user; see note | none | |

Result is one of `pass`, `fail`, `blocked`, `not run`. Only `pass` counts toward the score. The feature or gate closes at `n of n`.

## Notes

What blocked a rule, and defects seen outside the rules. Observations only; no fixes.
