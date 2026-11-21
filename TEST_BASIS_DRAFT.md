# Test Basis (DRAFT for team review)

Derived from reading the source at upstream commit `41387855b3154761925b4eb8a00660e7e661a5c8`
(files: `order/models.py`, `order/services.py`, `order/views.py`, `order/forms.py`,
`order/api_views.py`, `order/serializers.py`, `book/models.py`, `authentication/decorators.py`,
`authentication/permissions.py`, `seed_db.py`).

**Status:** nothing here has been run in the app yet. Before this becomes the final test basis,
(1) confirm the team's own `git rev-parse HEAD` matches the commit above, or re-check the files if
it does not, and (2) confirm every message text, URL and status code in the running app. Items
marked **VERIFY** are read from code but not observed.

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
| Anonymous | none | Web pages redirect to login; API answers 401 (**VERIFY**) |

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
| TB-FR-10 | both | A reader cannot lend or record a return (web 404, API 403); an anonymous caller is sent to sign in (web) or refused (API 401, **VERIFY**). |

Counts: Workflow 1 has 5, Workflow 2 has 4, plus 1 shared requirement. Requirements for the other
two members' areas can be added here by them.

## 4. Business rules

| ID | Type | Rule | Where in code | Test technique |
| --- | --- | --- | --- | --- |
| BR1 | Boundary / limit | Loan duration is an integer from **1 to 30 days** (default 14) | `IssueForm`, `LendForm` (`min_value=1`, `max_value=30`) | EP and 3-point BVA: 0, 1, 2 and 29, 30, 31 |
| BR2 | Boundary / limit | A loan can only start while available copies are **at least 1** | `check()` and `Order.save()` (`available_count <= 0` refuses) | BVA on available copies: 0 refused, 1 accepted; last-copy case |
| BR3 | Decision, two Boolean conditions | A reader has a **blocking overdue loan** when the loan is open **and** its due date is in the past; this refuses any new lend | `check()`: `end_at__isnull=True`, `plated_end_at__lt=now` | Decision table below |
| BR4 | State change | A loan moves Open to Returned when a return is recorded; recording again changes nothing; reopening an old loan (clearing the return date) needs a copy available | `_close_order`, `Order.save()` (`consumes_copy`), `OrderUpdateForm` | State transition testing, below |
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
| Returned | Reopen (edit, clear return date) | Open | Only if a copy is available; otherwise refused (**VERIFY**) |
| Open | Reopen | Open | No effect |
| (none) | Record return | n/a | Disallowed: no such loan (404) |

## 5. Items to check in the running app (possible defects or gaps)

These came out of the code reading and are not confirmed.

1. **API does not enforce the 1 to 30 day limit.** The web form validates `days`, but
   `POST /api/v1/order/` takes `plated_end_at` directly and `lend()` is called with `due=`. BR1 may
   hold in the UI only. This would be an API weakness and a high-value BVA finding. **VERIFY.**
2. **Past or inverted dates.** `plated_end_at` in the past via the API, or `end_at` earlier than
   `created_at` via **Edit** (`OrderUpdateForm`), may be accepted. **VERIFY.**
3. **Return on a closed loan through the API.** `PATCH` with a new `end_at` on a returned loan may
   overwrite the return date without any "already closed" protection that the web page has.
   **VERIFY.**
4. **Repeated lend requests.** Repeating the same `POST /api/v1/order/` should be refused by BR5
   (`already_on_loan`, 409). Confirm no duplicate rows (this is the "repeated requests" criterion).
5. **API loans recorded with `end_at` set.** `LendingMixin.create` saves such a loan as given
   ("a correction"), bypassing the availability and overdue checks. **VERIFY.**
6. **Reservations hold copies.** An active reservation reduces availability, so a lend can be
   refused with copies "on the shelf". Decide whether reservations are in scope; if not, keep the
   seed free of reservations (it is) and say so in the scope statement.

## 6. Cross-workflow check (shared record)

1. Read available copies of Kobzar (baseline 4).
2. Lend Kobzar to `alice@library.com` (not already holding it) and read back: 3.
3. Record the return and read back: 4.
4. Attempt to lend when available is 0 and read back: unchanged.

Read-back channels: book detail page, `GET /api/v1/book/<id>/` (**VERIFY** the field name for
availability in the API schema).

## 7. Open assumptions to record in the test basis

- The documentation (README, `docs/features/reservations.md`, `specs/003-priority-tech-debt/contracts/`)
  describes the reservation rules in detail but says little about plain loans. Loan rules BR1 to
  BR5 are therefore taken from the code and recorded as justified assumptions where documentation is silent.
- Time-dependent cases (overdue) need loans with a past due date. Use the API or the **Edit** screen to
  create them from the seed; do not wait for real time to pass.
