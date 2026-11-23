# Use Case Specification

SE3002 Software Quality Engineering, Final Project (Fall 2026).
System under test: Library-Django, Orders module. Baseline commit
`41387855b3154761925b4eb8a00660e7e661a5c8` (see `BASELINE.md`).

Requirement IDs (`TB-FR-xx`) and business rules (`BR1` to `BR5`) refer to `TEST_BASIS.md`.
Message texts are the exact texts observed in the app (`TEST_BASIS.md`, section 5).

## 1. How to write a use case (template)

Every member writes two use cases with this layout. Copy the block, keep the headings, and
replace the text. Number flows so that each Playwright test can name the flow it covers.

```
### UC-NN <short name: verb + object>

| Field | Value |
| --- | --- |
| Owner | <member> |
| Actor | <role, as seeded: librarian, reader, anonymous> |
| Goal | <what the actor wants to achieve> |
| Trigger | <what starts the use case> |
| Entry point | <URL or menu path> |
| Requirements | <TB-FR-xx, ...> |
| Business rules | <BRx, ...> |
| Test data | <accounts and records from the baseline, never hard-coded loan IDs> |

**Preconditions**
- <state that must be true before the use case starts>

**Postconditions (success)**
- <what is true in the database and on the screen afterwards>

**Postconditions (failure)**
- <what is guaranteed when a flow ends in a refusal; usually "nothing changed">

**Main flow (MF)**
1. <actor step>
2. <system response>

**Alternative flows (AF)**: the actor chooses a different valid path, or the goal is still reached.
- AF1 <name>: branches at MF step <n>. <steps>. Ends: <outcome>.
- AF2 ...

**Exception flows (EF)**: the system refuses or something fails, and the goal is not reached.
- EF1 <name>: branches at MF step <n>. <steps>. Message: "<exact text>". Ends: <outcome>.
- EF2 ...

**Automation map**
| Flow | Playwright test | Assertions (result shown and postcondition) |
| --- | --- | --- |
```

Rules for all six use cases:
- At least 2 alternative flows and at least 2 exception flows each.
- Every flow is automated in Playwright and asserts both the visible result (message or page)
  and the postcondition (for example the book's available copies, or the loan's status).
- Each test starts from `tests/team/baseline/reset.ps1`. Tests find records by name or email and
  never by loan ID, because IDs change between runs.
- Messages are copied from the app. Do not paraphrase them.

## 2. Use case overview

| ID | Name | Owner | Workflow |
| --- | --- | --- | --- |
| UC-01 | Lend a book to a reader | Maha | 1 |
| UC-02 | Record the return of a book | Maha | 2 |
| UC-03 | `<Hafsa>` | Hafsa | `<fill>` |
| UC-04 | `<Hafsa>` | Hafsa | `<fill>` |
| UC-05 | `<Umm-e-Sulaim>` | Umm-e-Sulaim | `<fill>` |
| UC-06 | `<Umm-e-Sulaim>` | Umm-e-Sulaim | `<fill>` |

## 3. Use cases

### UC-01 Lend a book to a reader

| Field | Value |
| --- | --- |
| Owner | Maha |
| Actor | Librarian (`librarian@library.com`) |
| Goal | Start a loan of one book for one reader |
| Trigger | A reader asks the librarian at the desk to borrow a book |
| Entry point | **Lend Directly**, `/order/lend/` |
| Requirements | TB-FR-01, TB-FR-02, TB-FR-03, TB-FR-04, TB-FR-05, TB-FR-10 |
| Business rules | BR1 (1 to 30 days), BR2 (a copy is available), BR3 (overdue), BR5 (already on loan) |
| Test data | Readers Bob Williams, Alice Smith and Oleh Melnyk; books Animal Farm (7 available), Kobzar (4 of 5 available), 1984 |

**Preconditions**
- The app is at the documented baseline (`BASELINE CLEAN`).
- The librarian is signed in.
- The chosen book has at least one available copy (BR2).
- The chosen reader has no overdue open loan (BR3) and does not already hold that book on an open loan (BR5).

**Postconditions (success)**
- A new loan exists for that reader and book, with no return date and a due date of now plus the chosen days.
- The book's available copies are one lower, and its total copies are unchanged (TB-FR-05).
- The librarian sees **All Orders**, with the banner `Lent “<book>” to <reader>, due <date>.`

**Postconditions (failure)**
- No loan is created and the available copies are unchanged.
- The librarian stays on the lend form with the reason shown.

**Main flow (MF)**
1. The librarian opens `/order/lend/`. The page **Lend Directly** shows Reader, Book and days (default 14).
2. The librarian selects the reader, selects the book and keeps or enters the loan days.
3. The librarian clicks **Lend Book**.
4. The system checks the days (1 to 30), that a copy is available, that the reader has no overdue loan and that the reader does not already hold the book.
5. The system creates the loan with due date now plus the days.
6. The system redirects to **All Orders** and shows `Lent “Animal Farm” to Bob Williams, due 23 Nov 2026.` (names and date as per the chosen data).
7. The new loan appears in the table with status **Active Loan**.

**Alternative flows (AF)**
- AF1 Shortest loan: branches at MF step 2. The librarian enters 1 day. Ends: the loan is created with a due date one day ahead; same success message and postconditions.
- AF2 Longest loan: branches at MF step 2. The librarian enters 30 days. Ends: the loan is created with a due date 30 days ahead (observed: `due 22 Dec 2026` from 22 Nov).
- AF3 Start from a book: branches at MF step 1. The librarian opens a book's page and clicks **Lend Directly**, which opens `/order/lend/?book=<id>` with the book already selected. Ends: as the main flow from step 2.

**Exception flows (EF)**
- EF1 Days below the minimum: branches at MF step 2. The librarian enters 0. The browser stops the form with `Value must be greater than or equal to 1` and nothing is sent. Ends: no loan.
- EF2 Days above the maximum: branches at MF step 2. The librarian enters 31. The browser stops the form with `Value must be less than or equal to 30`. Ends: no loan.
- EF3 Reader has an overdue loan: branches at MF step 4 (BR3). Message: `<reader> has an overdue loan: “<book>”, due <date>. It must be returned first.` Ends: no loan.
- EF4 Reader already has the book: branches at MF step 4 (BR5). Message: `<reader> already has “<book>” on loan.` Ends: no loan.
- EF5 No copy available: branches at MF step 4 (BR2). Message: `No copy of “<book>” is available. A reservation may be holding the last one.` Ends: no loan.
- EF6 Reader tries the page: a signed-in reader opens `/order/lend/` and gets the 404 page `Page not found` (TB-FR-10). Ends: no loan.

**Automation map** (to be completed with the Playwright spec names)

| Flow | Playwright test | Assertions (result shown and postcondition) |
| --- | --- | --- |
| MF | `uc01_main_flow` | Banner text; loan listed as Active Loan; available copies down by 1 |
| AF1 | `uc01_af1_one_day` | Due date one day ahead; available copies down by 1 |
| AF2 | `uc01_af2_thirty_days` | Due date 30 days ahead; available copies down by 1 |
| AF3 | `uc01_af3_from_book_page` | Book preselected; then as MF |
| EF1 | `uc01_ef1_days_zero` | Validation message; no new loan |
| EF2 | `uc01_ef2_days_31` | Validation message; no new loan |
| EF3 | `uc01_ef3_overdue_reader` | Refusal text; no new loan |
| EF4 | `uc01_ef4_already_on_loan` | Refusal text; no second loan |
| EF5 | `uc01_ef5_no_copy` | Refusal text; available copies still 0 |
| EF6 | `uc01_ef6_reader_denied` | 404 page; no loan |

### UC-02 Record the return of a book

| Field | Value |
| --- | --- |
| Owner | Maha |
| Actor | Librarian (`librarian@library.com`) |
| Goal | Close an open loan so the copy is available again |
| Trigger | A reader brings a book back to the desk |
| Entry point | **All Orders**, `/order/all/` |
| Requirements | TB-FR-06, TB-FR-07, TB-FR-08, TB-FR-09, TB-FR-10 |
| Business rules | BR4 (state change: open to returned, repeat changes nothing) |
| Test data | Kobzar loan by Oleh Melnyk (open at baseline, Kobzar 4 of 5 available); 1984 loan by Alice Smith |

**Preconditions**
- The app is at the documented baseline.
- The librarian is signed in.
- The loan is open (status **Active Loan**, no return date).

**Postconditions (success)**
- The loan has a return date and is closed.
- The book's available copies are one higher (Kobzar goes from 4 of 5 to 5 of 5).
- The librarian sees **All Orders**, with the banner `Return recorded: “Kobzar” is back in stock, and loan #<id> is closed.`
- The reader sees the loan as returned in **My Orders** (TB-FR-09).

**Postconditions (failure)**
- The loan and the available copies are unchanged.

**Main flow (MF)**
1. The librarian opens **All Orders** (`/order/all/`) and finds the open loan (status **Active Loan**).
2. The librarian clicks **Record Return**.
3. The system shows `Record the return of “Kobzar”?` with the reader, the borrowed time and the due time.
4. The librarian clicks **Yes, Record the Return**.
5. The system sets the return time to now.
6. The system redirects to **All Orders** and shows the success banner.
7. The loan now shows a returned time and no **Record Return** button.

**Alternative flows (AF)**
- AF1 Not now: branches at MF step 4. The librarian clicks **Not Now**. Ends: back on **All Orders**, loan still open, available copies unchanged.
- AF2 Return of an overdue loan: branches at MF step 1. The loan is already past due (created through the API, or via the Edit screen). The main flow runs unchanged. Ends: the loan is closed and the copy is available again.
- AF3 Reader checks the result: after MF step 7, the reader signs in and opens **My Orders**. Ends: the loan shows as returned (TB-FR-09).

**Exception flows (EF)**
- EF1 Loan already closed, opened directly: branches at MF step 3. The librarian opens `/order/close/<id>/` of a closed loan. The page says `This loan was already closed on 22 Nov 2026, 11:42 EET.` and offers only **Back to All Orders**. Ends: no change.
- EF2 Second submit of the same return: branches at MF step 4. The confirmation page was opened in two tabs, and the return was already recorded in the first. Submitting the second shows `Loan #<id> was already closed, so nothing changed.` Ends: the return time is unchanged and the available copies went up only once.
- EF3 Reader tries to record a return: a signed-in reader opens `/order/close/<id>/` and gets the 404 page (TB-FR-10, to be confirmed in the app). Ends: no change.
- EF4 Loan does not exist: the librarian opens `/order/close/<id>/` for an ID that does not exist. Ends: 404 page, nothing changes (to be confirmed in the app).

**Automation map** (to be completed with the Playwright spec names)

| Flow | Playwright test | Assertions (result shown and postcondition) |
| --- | --- | --- |
| MF | `uc02_main_flow` | Banner text; loan shows a returned time; Kobzar available 4 to 5 |
| AF1 | `uc02_af1_not_now` | Back on All Orders; loan still Active Loan; available unchanged |
| AF2 | `uc02_af2_overdue_loan` | Loan closed; copy available again |
| AF3 | `uc02_af3_reader_sees_returned` | My Orders shows the loan as returned |
| EF1 | `uc02_ef1_closed_loan_page` | Already-closed sentence; no Yes button |
| EF2 | `uc02_ef2_second_submit` | Info banner; return time unchanged; available up by 1 only |
| EF3 | `uc02_ef3_reader_denied` | 404 page; no change |
| EF4 | `uc02_ef4_unknown_loan` | 404 page; no change |

### UC-03 to UC-06

To be written by Hafsa and Umm-e-Sulaim with the template in section 1, then merged here.
