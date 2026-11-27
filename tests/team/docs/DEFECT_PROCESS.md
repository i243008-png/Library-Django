# Defect management process (Umm-e-Sulaim manages; everyone logs)
1. **Log** every defect as a GitHub Issue using the "Defect" template. Add labels: `defect`, one severity label (`sev-critical|high|medium|low`), one priority label (`P1|P2|P3`), one category label (`cat-validation`, `cat-business-rule`, `cat-access`, `cat-error-handling`, `cat-docs`, `cat-concurrency`, `cat-usability`, `cat-performance`).
2. **Triage** (twice a week, 10 minutes): confirm it reproduces, set severity/priority, write the triage decision in the issue.
3. **Lifecycle:** New -> Triaged -> In progress -> Fixed -> Verified -> Closed. Side exits: Rejected (not a defect), Deferred. A failed verification sets **Reopened** (counts toward the reopen rate).
4. **Record every defect also as a row in `defects.csv`** (the scripts read it). Never invent rows: only real issues.
5. **Severity guide:** Critical = data loss / security hole / rule bypass that corrupts stock. High = a rule fails or wrong status for a main flow. Medium = wrong error style/message, workaround exists. Low = cosmetic/documentation.
6. **Priority guide:** P1 fix before release, P2 fix if time, P3 note only.
7. **RCA** (5 Whys + fishbone) for the 2 most serious defects: `rca_template.md`, `python fishbone.py rca_1.json`.
8. **Pareto:** `python pareto.py` draws counts per category + cumulative % -> `results/pareto.png`.
9. Link every defect to a risk id from Hafsa's register and to the requirement it breaks.

## Weaknesses to CONFIRM first (my predictions from reading the code - they are NOT defects until a test or manual run proves them)
| ID | Prediction | How to confirm | Suggested category / severity |
|---|---|---|---|
| W1 | API accepts a `plated_end_at` in the past (loan overdue at birth) | `test_w1...` shows XFAIL | Validation / Medium |
| W2 | API has no maximum loan period (form limits to 30 days) | `test_w2...` XFAIL | Validation / Medium |
| W3 | Return time earlier than loan creation accepted | `test_w3...` XFAIL | Validation / Medium |
| W4 | Reopen refusal is 400 `{book}` but lending refusal is 409 `{code}` | `test_w4...` XFAIL | Error handling / Low |
If a `test_w*` shows **XPASS**, my prediction was wrong: do not log a defect, note it in the weakness list as "checked, not present".
