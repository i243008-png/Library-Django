# Usability walkthrough

Manual check of the two workflows, done by the tester on a clean baseline (`reset.ps1`).
Record real observations only. Evidence (screenshots) goes in `tests/team/evidence/usability/`.

Run on: `2026-11-25`  Browser: `Opera One 140.0.6074.18`  Screen: `1744 x 981 browser window, and 375 x 667 (DevTools device toolbar)`  Tester: Maha

## Tasks

| Task | Start | Success when | Done? | Time (s) | Wrong clicks or errors | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| T1 Lend Animal Farm to Bob for 7 days | Signed in as librarian, home page | The banner "Lent ..." appears | Yes | 59.4 | None | Time includes signing in and finding the lend page. Banner: Lent “Animal Farm” to Bob Williams, due 2 Dec 2026. Nothing confusing. |
| T2 Record the return of that loan | All Orders | The banner "Return recorded ..." appears | Yes | 11.5 | None | Banner: Return recorded: “Animal Farm” is back in stock, and loan #4 is closed. Nothing confusing. |
| T3 Find out why a lend was refused | Lend form, reader who already has the book | The reason is understood from the message alone | Yes | 20.6 | None | Message: Alice Smith already has “1984” on loan. The reason (a reader cannot hold two loans of the same book) was clear from the message alone. |
| T4 As a reader, check which books are on loan | Signed in as reader | My Borrowed Books shows the loans | Yes | 41.8 | None | The Kobzar loan is listed with status Active (not returned). Nothing confusing. |

## Checks (Pass / Fail / Not applicable, with a note)

| Check | Lend form | All Orders | Return page | My Orders |
| --- | --- | --- | --- | --- |
| Complete with the keyboard only (Tab, Enter, no mouse) | Pass. Tab, Shift+Tab, Enter and the arrow keys work; the order follows the screen. | Pass. Tab moves through the controls in order. | Pass. Tab reaches Yes, Record the Return and Not Now; Enter works on Not Now. | Pass. Tab reaches the navigation links (Books catalog, For you, My borrowed books); the page has no other controls. |
| A visible focus marker on every control | Pass. Blue highlight around the active field. | Pass. Blue highlight around each control. | Pass. Blue highlight around the active control. | Pass. Blue highlight on the navigation links. |
| Every field has a visible label | Pass. All fields have visible labels. | n/a | n/a | n/a |
| Error and success messages are clear and say what to do | Pass. Lent “Clean Code: A Handbook of Agile Software Craftsmanship” to Alice Smith, due 9 Dec 2026. The refusal states the cause but gives no next step (A11Y-02). | Pass. Return recorded: “Clean Code: A Handbook of Agile Software Craftsmanship” is back in stock, and loan #6 is closed. | Pass. Return recorded: “1984” is back in stock, and loan #2 is closed. | n/a |
| Readable and usable at 375 px wide (no sideways scrolling) | Pass. Fits without sideways scrolling. | Pass. Fits without sideways scrolling. | Pass. Fits without sideways scrolling. | Pass. Fits without sideways scrolling. |
| Text can be zoomed to 200% without losing content | Pass (measured). At 872 px (200% on a 1744 px window) the content fits (reflow-results.json). Not re-checked by hand: the site was slow. | Fail. At 872 px the table is about 1160 to 1170 px wide, so it needs sideways scrolling and the Record Return column is off-screen (A11Y-03). | Pass (measured). Content fits at 872, 640 and 320 px (reflow-results.json). Not re-checked by hand: the site was slow. | Pass. Manual check at exactly 200%: everything fits and nothing is cropped. Measured at 872 px: fits (reflow-results.json). |

## Automated results

| Tool | Version | Pages | Result | Evidence |
| --- | --- | --- | --- | --- |
| axe-core (Playwright, WCAG 2.0, 2.1 and 2.2 A and AA) | axe-core 4.14.1, @axe-core/playwright 4.14.0 | 9 page states: login, books, lend form, lend form with error, lend form at 375 px, All Orders, return confirmation, My Orders, 404 | 0 violations. 1 rule marked "needs review" (colour contrast of the decorative arrow on the books page), reviewed manually: see A11Y-01 | `tests/team/evidence/accessibility/axe-results.json` |
| Reflow check | Playwright 1.65.1, Chromium | 6 pages (login, books, lend form, All Orders, My Orders, return page) at 872, 640 and 320 px | 18 checks: 17 pass, 1 fails (All Orders at 872 px: content about 1160 to 1170 px wide in an 872 px window; 1173 px and 1163 px in two runs), see A11Y-03 | `tests/team/evidence/usability/reflow-results.json` |
| Lighthouse, accessibility category (CLI, headless Chromium) | 12.8.2 | Login page | Score 100, 0 failed audits, 10 items listed for manual check | `tests/team/evidence/accessibility/lighthouse-login.report.html` |
| Lighthouse, accessibility category (DevTools panel, emulated desktop, navigation mode) | 13.5.0 (Chromium 157) | Lend form, All Orders | Lend form: score 100, 0 failed audits, 24 passed, 39 not applicable. All Orders: score 100, 0 failed audits, 23 passed, 40 not applicable. Both list 10 items for manual check. Captured 2026-11-27. A first All Orders run failed with NO_FCP (page did not paint) and was repeated. | `tests/team/evidence/accessibility/lighthouse-lend-form.report.html`, `tests/team/evidence/accessibility/lighthouse-all-orders.report.html` |
## Findings

| ID | Page | Observation | Heuristic or WCAG criterion | Severity | Outcome and linked risk |
| --- | --- | --- | --- | --- | --- |
| A11Y-01 | Books catalogue | axe-core marked colour contrast as "needs review" for the decorative arrow in the Details buttons (9 elements, aria-hidden) | WCAG 1.4.3 (decorative text is exempt) | None | Reviewed manually: text rgb(51 65 85) on rgb(241 245 249), ratio 9.45:1 (WebAIM checker), passes 4.5:1, decorative, not a violation. No linked risk. |
| A11Y-02 | Lend form | The refusal "Alice Smith already has “1984” on loan." states the cause but suggests no next step | Usability heuristic: help users recognise, diagnose and recover from errors | Low | Observation only; the cause was understood from the message alone in T3 |
| A11Y-03 | All Orders | At 872 px wide (200% zoom on a 1744 px window) the orders table is about 1160 to 1170 px wide and does not fit. The Status / Actions column, which holds Record Return, is off-screen until the table is scrolled sideways. The table appears from 768 px; below that the page shows cards, which fit (checked at 640 and 320 px). | WCAG 1.4.10 Reflow (data tables are an exception) and 1.4.4 Resize Text (content reachable by scrolling, nothing lost); usability: the main action is hidden off-screen | Low | Open. Measured: tests/team/evidence/usability/reflow-results.json (1173 px and 1163 px in two runs; the width varies with the data). Possible fix: show the cards up to about 1200 px, or keep the actions column visible. GitHub issue #15. |
