# Test Basis

Derived from reading the source at upstream commit `41387855b3154761925b4eb8a00660e7e661a5c8`
(files: `order/models.py`, `order/services.py`, `order/views.py`, `order/forms.py`,
`order/api_views.py`, `order/serializers.py`, `book/models.py`, `authentication/decorators.py`,
`authentication/permissions.py`, `seed_db.py`).

**Status:** the API checks (5.2) were run on 2026-11-22 from a clean baseline (`tests/team/baseline/reset.ps1`, output `BASELINE CLEAN`). The web page checks (5.1) were run earlier the same day, before a second reset, so one loan ID in their messages (#8) is not a baseline ID. The message texts do not depend on it, and tests must never hard-code loan IDs. Evidence is in `tests/team/evidence/test-basis/`.

## 1. Scope and workflows

Module: Orders (a "loan" is an `Order` row).

| | Workflow 1: Lend a book | Workflow 2: Return a book |
| --- | --- | --- |
| Starting condition | Librarian signed in; a reader and a book with at least one available copy exist | A loan exists with no return date (open) |
| User action | Librarian opens **Lend Directly** (`/order/lend/`), picks reader, book and loan days, clicks **Lend Book**. API: `POST /api/v1/order/` | Librarian opens **All Orders** (`/order/all/`), clicks **Record Return**, confirms with **Yes, Record the Return** (`/order/close/<id>/`). API: `PATCH /api/v1/order/<id>/` with `end_at` |
| Expected outcome | A loan is created, open, with due date = now + days; the book's available copies fall by 1 | The loan gets a return date and is closed; the book's available copies rise by 1 |

**Wording to correct in the work-division document.** In this version of the code a reader cannot
borrow directly. `order_create` redirects readers to the book page, where they can only reserve
(`POST /order/reserve/<book_id>/`, `POST /api/v1/reservation/`). Only a librarian creates a loan
(`FR-015` in the code comments; API create is `IsLibrarian`). Workflow 1 should therefore be
described as "Lend a book (librarian creates a loan)", not "Reader borrows a book". The reader's
role in the project is the denied side of the access checks plus viewing their own loans.

**Shared record:** a book's available copies. Workflow 1 consumes one; Workflow 2 releases one.
Computed, never stored: `available = count - open loans - active unexpired reservations`, minimum 0
(`Book.available_count`).

## 2. Roles

| Role | Seeded account | Permissions (from code) |
| --- | --- | --- |
| Librarian | `librarian@library.com` | Lend, record returns, edit and delete loans, see all loans (`/order/all/`), lend and manage reservations |
| Reader | `reader@library.com`, `alice@library.com`, `bob@library.com` | See own loans only (`/order/my/`, API returns 404 for another reader's loan); reserve books; cannot lend or return |
| Anonymous | none | Web pages redirect to login; API answers 401 with `WWW-Authenticate: Session` and body `Authentication credentials were not provided.` (observed, evidence 11) |

Denied-access responses differ by channel, and tests must assert the right one:
librarian-only web pages answer **404** to a signed-in reader (`librarian_required`), API write
operations answer **403** to a reader (`IsLibrarian`), and another reader's loan answers **404** in the API.

## 3. Functional requirements (team IDs)

| ID | Workflow | Requirement |
| --- | --- | --- |
| TB-FR-01 | 1 | A librarian can lend an available book to a chosen reader for 1 to 30 days. The loan is created open (no return date) with due date = now + days, and the page shows a "Lent ... due ..." confirmation. |
| TB-FR-02 | 1 | Lending is refused when no copy is available, with an explanatory message, and nothing changes. |
| TB-FR-03 | 1 | Lending is refused when the reader has an overdue open loan, naming the overdue book and its due date. |
| TB-FR-04 | 1 | Lending is refused when the reader already has that book on an open loan. |
| TB-FR-05 | 1 | A successful lend reduces the book's available copies by exactly 1 (total copies unchanged). |
| TB-FR-06 | 2 | A librarian can record a return after a confirmation step. The loan gets a return date and the page shows a "Return recorded ... back in stock" confirmation. |
| TB-FR-07 | 2 | A recorded return increases the book's available copies by exactly 1. |
| TB-FR-08 | 2 | Recording a return on an already closed loan changes nothing and shows an "already closed" message. |
| TB-FR-09 | 2 | A reader sees their own loans, with returned or open status, in My Orders and cannot see another reader's loans. |
| TB-FR-10 | both | A reader cannot lend or record a return (web 404, API 403 from the code; not exercised in the app); an anonymous caller is sent to sign in (web) or refused (API 401, observed). |

Counts: Workflow 1 has 5, Workflow 2 has 4, plus 1 shared requirement. Requirements for the other
two members' areas can be added here by them.

## 4. Business rules

| ID | Type | Rule | Where in code | Test technique |
| --- | --- | --- | --- | --- |
| BR1 | Boundary / limit | Loan duration is an integer from **1 to 30 days** (default 14) | `IssueForm`, `LendForm` (`min_value=1`, `max_value=30`) | EP and 3-point BVA: 0, 1, 2 and 29, 30, 31. Evidence today: web form checks (5.1, evidence 01 to 04). Form unit tests to be added (Hafsa). |
| BR2 | Boundary / limit | A loan can only start while available copies are **at least 1** | `check()` and `Order.save()` (`available_count <= 0` refuses) | BVA on available copies: 0 refused, 1 accepted; last-copy case |
| BR3 | Decision, two Boolean conditions | A reader has a **blocking overdue loan** when the loan is open **and** its due date is in the past; this refuses any new lend | `check()`: `end_at__isnull=True`, `plated_end_at__lt=now` | Decision table below |
| BR4 | State change | A loan moves Open to Returned when a return is recorded; recording again changes nothing; reopening an old loan (clearing the return date) needs a copy available | `_close_order`, `Order.save()` (`consumes_copy`), `OrderUpdateForm` | State transition testing, below. Evidence today: manual check (5.1, evidence 09 and 10). Unit test for a repeated return to be added (Hafsa). |
| BR5 | Decision (extra) | A reader cannot hold two open loans of the same book | `check()`: `already_on_loan` | EP |

### BR3 decision table (conditions: C1 loan is open, C2 due date is before now)

| Case | C1 open | C2 past due | Blocks new lend? |
| --- | --- | --- | --- |
| 1 | T | T | Yes (refused as overdue) |
| 2 | T | F | No |
| 3 | F (returned) | T | No |
| 4 | F (returned) | F | No |

### BR4 loan state transitions

| From | Action | To | Allowed? |
| --- | --- | --- | --- |
| (none) | Lend | Open | Yes, if a copy is available (BR2) and BR3, BR5 pass |
| Open | Record return | Returned | Yes |
| Returned | Record return again | Returned (no change) | Yes, but idempotent: message only, return date not changed |
| Returned | Reopen (edit, clear return date) | Open | Only if a copy is available; otherwise refused (from the code; not exercised in the app) |
| Open | Reopen | Open | No effect |
| (none) | Record return | n/a | Disallowed: no such loan (404) |

## 5. Observed results (running app, clean baseline)

### 5.1 Web pages

| Check | Observed | Evidence |
| --- | --- | --- |
| Lend Directly, days = 0 | `Value must be greater than or equal to 1` | 01 |
| Lend Directly, days = 31 | `Value must be less than or equal to 30` | 02 |
| Lend Directly, days = 1 (Bob, Animal Farm) | `Lent "Animal Farm" to Bob, due 23 Nov 2026` | 03 |
| Lend Directly, days = 30 (Alice, Animal Farm) | `Lent "Animal Farm" to Alice, due 22 Dec 2026` | 04 |
| Kobzar available copies before and after a return | `Before: 4 of 5 available, After: 5 of 5 available` | 05, 08 |
| Return confirmation page | `Reader: Oleh Melnyk (reader@library.com) Borrowed: 22 Nov 2026, 11:43 EET Due: 6 Dec 2026, 11:43 EET` | 06 |
| Return recorded banner | `Return recorded: “Kobzar” is back in stock, and loan #8 is closed.` | 07 |
| Direct URL `/order/close/<id>/` of a closed loan | `This loan was already closed on 22 Nov 2026, 11:42 EET` | 09 |
| Second submit of the same return (two tabs) | `Loan #2 was already closed, so nothing changed.` | 10 |
| Signed-out `GET /api/v1/order/` | **401 Unauthorized**, header `WWW-Authenticate: Session`, body `{"detail": "Authentication credentials were not provided."}` | 11 |
| Reader opens `/order/lend/` | `Page not found` | 12 |

### 5.2 API checks (librarian session, browser console)

Raw output: `tests/team/evidence/test-basis/api-checks-raw-output.txt`. Baseline commit
`41387855b3154761925b4eb8a00660e7e661a5c8`.

| ID | Request | Status and result | Conclusion | Evidence |
| --- | --- | --- | --- | --- |
| V1 | `POST /api/v1/order/` Bob, Animal Farm, due date 400 days ahead | **201**, loan #4 created, due 27 Dec 2027 | The API accepts a loan period the web forms refuse (1 to 30 days) | 13 |
| V2 | `POST /api/v1/order/` Alice, Kobzar, due date 5 days in the past | **201**, loan #5 created, due 17 Nov 2026 | The API accepts a loan that is overdue when created | 14 |
| V3 | `POST /api/v1/order/` Alice, Animal Farm, due in 7 days (Alice now overdue) | **409**, code `overdue_loan`, "Alice Smith has an overdue loan: “Kobzar”, due 17 Nov 2026. It must be returned first." | BR3 holds in the API | 15 |
| V4 | Repeat of V1 for Bob | **409**, code `already_on_loan`, "Bob Williams already has “Animal Farm” on loan." No second loan created | BR5 holds; a repeated request creates no duplicate | 16 |
| V5 | `PATCH /api/v1/order/3/` `{end_at: now + 3 days}` on the seeded returned loan | **200**, return date changed from 20 Nov 2026 to **25 Nov 2026** (a future date) | Nothing protects a closed loan's return date, and a future return date is accepted | 17 |
| V6 | `POST /api/v1/order/` Alice, Animal Farm, with `end_at` set, while Alice is overdue | **201**, loan #6 created already returned | A loan created with a return date skips the overdue check (documented in the code as a correction) | 18 |

### 5.3 Effect on the business rules

| Rule | Web forms | API |
| --- | --- | --- |
| BR1 loan period 1 to 30 days | Enforced by `IssueForm` and `LendForm` (observed in 5.1) | **Not enforced** (V1, V2) |
| BR2 a copy must be available | Not exercised in the app; covered by unit tests | Not exercised in the app |
| BR3 overdue loan blocks a new loan | Not exercised in the web form | Enforced (V3) |
| BR4 return and state change | Return recorded once; a repeat changes nothing (5.1) | Closed loan's return date can be rewritten (V5) |
| BR5 same book already on loan | Not exercised in the web form | Enforced (V4) |

## 6. Cross-workflow check (shared record)

1. Read available copies of Kobzar (baseline 4).
2. Record the return of the open Kobzar loan and read back: 5 (observed in 5.1, evidence 05 and 08).
3. Read-back channel: the book detail page badge ("N of M Available") and `GET /api/v1/book/<id>/`,
   which returns an `available_count` field (observed in the book API response used by the checks).

## 7. Assumptions and open points

- **Loan period in the API.** The 1 to 30 day limit comes from the web forms. The README does not state
  it as an API rule. Assumption: the intended rule applies to the API as well, so V1 and V2 are logged
  as an inconsistency between channels. Umm-e-Sulaim's generator limits for `plated_end_at` depend on
  this decision, so the team must confirm it.
- **Reservations.** An active reservation reduces availability. They are out of scope for the two
  workflows. The seed has no reservations.
- **Documentation gap.** The README, `docs/features/reservations.md` and `specs/003-priority-tech-debt/contracts/`
  describe reservations in detail but say little about plain loans. Rules BR1 to BR5 are taken from the
  code and recorded as justified assumptions where the documentation is silent.
- **Seed dates.** The seeded returned loan (#3, Bob, Clean Code) has a return date (20 Nov 2026) earlier
  than its `created_at` (22 Nov 2026), because the seed sets dates in the past while `created_at` is the
  seed time. Tests that compare these two fields must not rely on the seeded loan.
- **Time-dependent cases.** Overdue cases need a loan with a past due date. Create it through the API
  (as V2 does) or the Edit screen; do not wait for real time to pass.
- **Repeated runs.** Every check above changes the data. Run `tests/team/baseline/reset.ps1` before each
  run.
