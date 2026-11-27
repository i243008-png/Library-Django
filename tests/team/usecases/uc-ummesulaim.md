# Use cases by Umm-e-Sulaim (UC-05 and UC-06)

Layout copied from section 1 of USE_CASES.md. Message texts come from the app source and are
checked by the Playwright tests (tests/team/usecases/test_uc05_uc06.py). Fill the
`<TB-FR-xx>` ids from TEST_BASIS.md before merging.

### UC-05 Reserve a book and have it issued as a loan

| Field | Value |
| --- | --- |
| Owner | Umm-e-Sulaim |
| Actor | Reader (`bob@library.com`, Bob Williams), then Librarian (`librarian@library.com`) |
| Goal | The reader holds a copy, then collects it and starts a loan |
| Trigger | A reader wants a book and reserves it before coming to the desk |
| Entry point | The book's page, button **Reserve for N Hours** (`/book/<id>/`); then **Reservation Desk** (`/order/reservations/desk/`) |
| Requirements | `<TB-FR-xx>` (reserve, issue, loan period) |
| Business rules | BR1 (1 to 30 days), BR2 (a copy is available), BR3 (overdue), BR5 (already reserved or on loan) |
| Test data | Reader Bob Williams; a book created by the test's own set-up with a unique name (QA-xxxxxxxx) and 5 copies |

**Preconditions**
- The app is at the documented baseline (`BASELINE CLEAN`).
- The reader is signed in, has no overdue loan, and has not reserved this book.
- The book has at least one available copy.

**Postconditions (success)**
- The reservation is issued and one open loan exists for that reader and book.
- The book's available copies are one lower than before the reservation, and they stay that way after issuing (the held copy became the loan).
- The librarian sees the banner `Issued “<book>” to Bob Williams as loan #<id>, due <date>.`

**Postconditions (failure)**
- No reservation or loan is created, and the available copies are unchanged.

**Main flow (MF)**
1. The reader opens the book's page.
2. The reader clicks **Reserve for N Hours**.
3. The system holds one copy and opens **My Reservations** with `Reserved “<book>”. Collect it from a librarian before <deadline>.`
4. The reader collects the book at the desk. The librarian opens **Reservation Desk** and clicks **Issue** on that reservation.
5. The system shows **Issue Reservation** with the reader, the book and the deadline, and the days field (default 14).
6. The librarian keeps 14 days and clicks **Issue Book**.
7. The system starts the loan and returns to the desk with `Issued “<book>” to Bob Williams as loan #<id>, due <date>.`

**Alternative flows (AF)**
- AF1 Longest loan: branches at MF step 6. The librarian enters 30 days. Ends: the loan is due 30 days after it starts; same banner.
- AF2 Shortest loan: branches at MF step 6. The librarian enters 1 day. Ends: the loan is due 1 day after it starts; same banner.
- AF3 Reader cancels: branches at MF step 4. The reader opens **My Reservations**, clicks **Cancel**, then **Yes, Cancel Reservation**. Message: `Cancelled your reservation of “<book>”.` Ends: the copy is free again and no loan exists.

**Exception flows (EF)**
- EF1 Book already reserved: branches at MF step 2. The page shows `You already reserved “<book>”. Collect it from a librarian before <deadline>.` instead of the Reserve button. Ends: still one reservation, one copy held.
- EF2 Reader has an overdue loan: branches at MF step 2. The page shows `“<book>” was due on <date>. Return it before reserving or borrowing another book.` and no Reserve button. Ends: nothing reserved.
- EF3 No copy available: branches at MF step 2. The page shows `No copy of “<book>” is available right now. Try again later or choose another book.` Ends: nothing reserved.
- EF4 Reservation already issued: branches at MF step 5. The librarian opens the issue page of a reservation that already became a loan. The page shows `This reservation was already issued as loan #<id>.` and no **Issue Book** button. Ends: still exactly one loan.

**Automation map**

| Flow | Playwright test | Assertions (result shown and postcondition) |
| --- | --- | --- |
| MF | `test_uc05_main_reserve_then_issue` | Reserved banner; copies 5 to 4; Issued banner; one open loan; copies still 4 |
| AF1 | `test_uc05_af1_issue_for_30_days` | Issued banner; due 30 days after start |
| AF2 | `test_uc05_af2_issue_for_1_day` | Issued banner; due 1 day after start |
| AF3 | `test_uc05_af3_reader_cancels_own_reservation` | Cancelled banner; copies back to 5; no loan |
| EF1 | `test_uc05_ef1_book_already_reserved` | Refusal text, no Reserve button; copies stay at 4 |
| EF2 | `test_uc05_ef2_reader_has_an_overdue_loan` | Refusal text, no Reserve button; copies stay at 5 |
| EF3 | `test_uc05_ef3_no_copy_available` | Refusal text, no Reserve button; copies stay at 0 |
| EF4 | `test_uc05_ef4_reservation_already_issued` | Already-issued text, no Issue Book button; one loan |

### UC-06 Correct a loan on the Edit screen

| Field | Value |
| --- | --- |
| Owner | Umm-e-Sulaim |
| Actor | Librarian (`librarian@library.com`) |
| Goal | Fix a loan's planned return time, or its returned time, after it was recorded |
| Trigger | A date was recorded wrongly, or a return was recorded by mistake |
| Entry point | **Edit** on a loan in **All Orders**, `/order/update/<id>/` |
| Requirements | `<TB-FR-xx>` (correct a loan, return, reopen) |
| Business rules | BR2 (a copy is available), BR4 (state change: open to returned, returned to open) |
| Test data | Reader Bob Williams; books created by the test's own set-up (unique QA-xxxxxxxx names) |

**Preconditions**
- The app is at the documented baseline.
- The librarian is signed in and the loan exists.

**Postconditions (success)**
- The loan keeps the new values, and the librarian sees `Changes to loan #<id> saved.`
- The book's available copies reflect the loan state: up by 1 when a return time is set, down by 1 when a returned loan is reopened.

**Postconditions (failure)**
- The loan and the available copies are unchanged.

**Main flow (MF)**
1. The librarian opens the Edit screen of an open loan (**Edit Order #<id>**).
2. The librarian sets a later **Planned Return Date & Time**.
3. The librarian clicks **Save Order Changes**.
4. The system saves and shows `Changes to loan #<id> saved.` on **All Orders**.

**Alternative flows (AF)**
- AF1 Record the return here: branches at MF step 2. The librarian fills **Actual Return Date & Time**. Ends: the loan is returned and the copy is available again.
- AF2 Reopen a returned loan: branches at MF step 2, on a returned loan. The librarian clears **Actual Return Date & Time**. Ends: the loan is open again, copies down by 1 (a copy was free).
- AF3 Cancel: branches at MF step 3. The librarian clicks **Cancel**. Ends: back on **All Orders**, nothing changed.

**Exception flows (EF)**
- EF1 Reopen with no free copy: branches at MF step 3 (BR2, BR4). Message: `No copies of this book are currently available.` Ends: stays on the form, loan still returned.
- EF2 Planned return left empty: branches at MF step 3. The browser blocks the form. Ends: nothing sent, nothing changed.
- EF3 Reader opens the Edit screen: a signed-in reader gets the 404 page. Ends: no change.

**Automation map**

| Flow | Playwright test | Assertions (result shown and postcondition) |
| --- | --- | --- |
| MF | `test_uc06_main_extend_planned_return` | Saved banner; due date moved; loan still open; copies unchanged |
| AF1 | `test_uc06_af1_record_the_return_on_the_edit_screen` | Saved banner; return time set; copies 4 to 5 |
| AF2 | `test_uc06_af2_reopen_a_returned_loan_when_a_copy_is_free` | Saved banner; loan open; copies 1 to 0 |
| AF3 | `test_uc06_af3_cancel_leaves_the_loan_unchanged` | Back on All Orders; loan identical; copies unchanged |
| EF1 | `test_uc06_ef1_reopen_refused_when_no_copy_is_free` | Error text, stays on the form; loan still returned; copies 0 |
| EF2 | `test_uc06_ef2_planned_return_cannot_be_empty` | Form blocked by the browser; loan identical |
| EF3 | `test_uc06_ef3_a_reader_cannot_open_the_edit_screen` | 404; no Save button; loan unchanged |
