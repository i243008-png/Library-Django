# Test Plan - Django Library, Orders module (Borrow and Return)
Owner of this document: Umm-e-Sulaim Rana (24i-3062). Version 1.0 - update at the end of every phase (see Change log).
System: https://github.com/Arezzon/Library-Django (MIT). Baseline commit: *(paste Maha's `git rev-parse HEAD` here)*.

## 1. Scope
**In scope:** Workflow 1 *Borrow a book* (librarian lends: `POST /api/v1/order/`, web `/order/lend/`, reservation issue `POST /api/v1/reservation/{id}/issue/`) and workflow 2 *Return a book* (`PATCH /api/v1/order/{id}/` setting `end_at`, web `/order/close/{id}/`). **Shared record:** the book's `available_count` (= copies - open loans - active reservations).
**Out of scope:** AI assistant, recommendations, ratings, analytics/Celery, user registration, admin site, book search. Reservation cancel/expiry is used only as set-up.
**Roles:** Reader (reader@, alice@, bob@library.com) and Librarian (librarian@library.com).

## 2. Test basis (requirements, rules)
Source: `order/models.py`, `order/services.py`, `order/api_views.py`, `order/serializers.py`, README; assumptions are listed in 2.3.
### 2.1 Functional requirements (traceability in traceability.csv)
| ID | Requirement |
|---|---|
| FR-B1 | A librarian can lend an available book to a reader; the loan is open and keeps its due date. |
| FR-B2 | Lending reduces the book's available copies by one. |
| FR-B3 | Lending is refused when no copy is available; nothing changes. |
| FR-B4 | Lending is refused when the reader has an overdue loan. |
| FR-B5 | Lending is refused when the reader already holds the same book. |
| FR-B6 | Only librarians may lend (reader gets 403, anonymous 401). |
| FR-B7 | Invalid borrow input (user, book, plated_end_at, end_at) is refused with 400 naming the field. |
| FR-B8 | A reservation is issued as a loan of 1 to 30 days (default 14); outside the range is refused; a repeated issue starts no second loan. |
| FR-R1 | A librarian records a return by setting `end_at`; the loan becomes closed. |
| FR-R2 | A return increases available copies by one. |
| FR-R3 | A repeated return changes nothing more (no extra copy, no duplicate loan). |
| FR-R4 | Reopening a returned loan is allowed only when a copy is free. |
| FR-R5 | A reader sees only their own loans (others answer 404); a librarian sees all. |
| FR-R6 | Invalid `end_at` is refused with 400. |
| FR-R7 | Only librarians change or delete a loan. |
### 2.2 Business rules
| ID | Rule | Kind |
|---|---|---|
| BR1 | A loan starts only if available copies >= 1. | Boundary / limit |
| BR2 | A loan is refused if (A) the reader has an overdue loan OR (B) the reader already holds the same book. Checked in that order. | Decision, 2 Boolean conditions |
| BR3 | A loan moves open -> returned by setting `end_at`; returned -> open (reopen) only when a copy is free. | State change |
| BR4 | Only librarians start/change/delete loans; readers read only their own. | Role / permission |
Extra limit: loan period 1 to 30 days when a reservation is issued (and on the desk form).
### 2.3 Justified assumptions
- A1: The API field `plated_end_at` (planned return) has no stated limit in the code; the desk form limits the period to 1-30 days. We assume the **API should enforce the same** (weakness tests W1, W2).
- A2: "Returned twice" is assumed harmless (idempotent). Verified in code: second `PATCH` does not change copies.
- A3: Test accounts are the repo's own seeded demo accounts; no real data is used.

## 3. Approach by risk level
Risk scores come from Hafsa's risk register (L x I, 1-5). Until it is merged, this is my working mapping:
| Risk level | Areas | Technique and depth at API level |
|---|---|---|
| High (>= 15) | BR1 availability, BR2 overdue/duplicate, concurrent duplicate borrow | EP + 3-point BVA, decision table (4 combos), concurrency test, read-back after success and rejection |
| Medium (8-14) | BR3 state change, BR4 roles, days limit 1-30 | State-transition tests (allowed + disallowed), role matrix, EP + 3-point BVA from generator |
| Low (<= 7) | Error-message wording, list endpoints | Single happy-path check |
Techniques: EP, BVA (3-point), decision table, state transition, error guessing (weakness tests), concurrency.

## 4. Test levels owned by me
API and integration (pytest + requests): `tests/team/api/`. Test data: generator output `results/cases.json`. Coverage criteria: endpoint+method, status code, request field, role (`api_coverage.py`).

## 5. Environment
Docker Desktop, `docker compose up --build`, app at http://localhost:8000, PostgreSQL. Reset between runs: `docker compose down -v` then `up` (or Maha's `reset.ps1`). Python 3.12, pytest, requests, PyYAML. Tool versions: record with `pip freeze` into `tests/team/docs/TOOL_VERSIONS.txt`.

## 6. Test data
Seed accounts (repo's own): librarian@, reader@, alice@, bob@. Every test creates its own fresh book `QA-xxxxxxxx` through the API, so tests do not depend on each other. Generated EP/BVA values come from `openapi.yaml` through the generator.

## 7. Roles and responsibilities
| Person | Responsibility |
|---|---|
| Umm-e-Sulaim | API tests, generator, OpenAPI, test plan, estimates, traceability, defects, RCA, Pareto, weekly reports |
| Hafsa | Unit tests, SonarQube, mutation, CI gate, risk register, exit criteria |
| Maha | Baseline/reset, use cases, usability, security, performance, completion report |

## 8. Schedule (phases from the work division; adjust dates to the real deadline)
| Phase | Deliverable from me |
|---|---|
| 1 | Read code, write requirements/rules (this document, section 2) |
| 2 | Test plan v1, OpenAPI spec, generator, estimates |
| 3 | API tests, regeneration demo, coverage table, defects logged |
| 4 | RCA (2 defects), Pareto, weekly report 3-4 |
| 5 | Final numbers to Maha, actual-vs-estimate comparison |

## 9. Entry, exit, suspension, resumption criteria
- **Entry:** app starts from the baseline commit; reset script ends with BASELINE CLEAN; spec exists; seed accounts can log in.
- **Exit (API level):** (E1) 100% of FR-B*/FR-R* have at least one executed test; (E2) 100% of generated EP/BVA cases executed, no unexplained failure; (E3) endpoint+method coverage 100%, status-code coverage >= 90% of documented codes; (E4) 0 open Critical/High defects. Hafsa's register ties E1-E4 to the highest risks.
- **Suspension:** app down, login broken, seed data missing, or > 20% of tests failing for an environment reason. **Resumption:** reset to baseline, rerun smoke (`pytest -k "br4_anonymous or br3_open_to_returned"`), then continue.

## 10. Risks to the testing (project risks, also in the register)
PR1 Group members' schedules clash with deadlines (L3 x I4). PR2 Docker/PostgreSQL environment breaks or is slow (L3 x I4). PR3 Upstream repo changes underneath us - mitigated by never running `git pull` after the baseline.

## 11. Estimation (three-point: E = (O + 4M + P) / 6, hours)
| Area | O | M | P | E | Actual (fill in at the end) |
|---|---|---|---|---|---|
| Read code and write test basis | 2 | 4 | 7 | 4.2 | |
| OpenAPI spec | 2 | 3 | 5 | 3.2 | |
| Generator + regeneration demo | 3 | 5 | 9 | 5.3 | |
| API tests (generated + rule tests) | 6 | 10 | 16 | 10.3 | |
| Coverage + weakness list | 2 | 3 | 5 | 3.2 | |
| Test plan + traceability | 3 | 4 | 6 | 4.2 | |
| Defects, RCA, Pareto | 3 | 5 | 8 | 5.2 | |
| Weekly reports (x4) | 2 | 3 | 4 | 3.0 | |
| Own use cases + Playwright | 4 | 6 | 10 | 6.3 | |
| **Total** | **27** | **43** | **70** | **45.0** | |

## 12. Change log
| Version | Date | Change |
|---|---|---|
| 1.0 | | First version |
