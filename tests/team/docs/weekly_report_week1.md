# Weekly progress report - Week 1
Author: Umm-e-Sulaim Rana (24i-3062) | Project: SQE Final Project (Django Library, Orders)

## 1. Plan vs actual
| Planned this week (test plan phases 1-3) | Done? | Hours planned | Hours actual | Variance |
|---|---|---|---|---|
| Read code, write test basis | Yes | 4.2 | (fill in) | |
| OpenAPI spec | Yes | 3.2 | (fill in) | |
| Generator + regeneration demo | Yes | 5.3 | (fill in) | |
| API tests (generated + rule + status-code tests) | Yes, 93 tests | 10.3 | (fill in) | |
| Coverage report | Yes, 100% | 3.2 | (fill in) | |
| Defect log | Yes, 6 defects (#9-#14) | 5.2 | (fill in) | |
| Own use cases + Playwright (UC-05, UC-06) | Yes | 6.3 | (fill in) | |

## 2. GQM metrics (run `python gqm_metrics.py --executed 93 --passed 87`)
| Question | Metric | Value this week | Last week | Target | Reading in context |
|---|---|---|---|---|---|
| Are all requirements tested? | Requirements coverage | 15/15 = 100% | n/a | 100% | Every requirement has at least one executed test |
| How buggy is the area? | Defect density (per 100 tests) | 6.5 | n/a | trend down | 6 defects in 93 tests; 4 of them in input validation |
| Is fixing reliable? | Reopen rate | n/a | n/a | < 10% | No defect fixed yet, so no reopen |
| Are API checks complete? | Endpoint / status-code / field coverage | 100% / 100% / 100% | n/a | endpoint 100%, status >= 90% | First run was 49% status-code coverage; 24 extra tests closed the gap |

## 3. Defects this week
New: 6 (1 High, 4 Medium, 1 Low). Closed: 0. Open: 6 (Critical 0 / High 1). See GitHub issues #9 to #14.

## 4. Control actions
| Problem seen | Control action | Owner | Due |
|---|---|---|---|
| Status-code coverage was 49%, below the 90% exit criterion | Added 24 tests for 401/403/404/400/204/409; coverage now 100% | Umm-e-Sulaim | done |
| Input validation produced 4 of 6 defects | Add boundary tests for every new input and ask for validators in the fix | Umm-e-Sulaim / Hafsa | week 2 |
| Risk ids missing in defects.csv (TBD) | Get ids from Hafsa's risk register | Umm-e-Sulaim | week 2 |

## 5. Risks / blockers
Port 8000 clashed with another Docker project (stopped it). Seeded data can be changed by hand edits, so evidence runs start from the reset script.

## 6. Plan for next week
RCA pictures, Pareto, traceability review, API spec check against /api/docs/, PR review with Hafsa, review Maha's Playwright and k6 scripts.
