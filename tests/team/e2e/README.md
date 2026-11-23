# Playwright use case tests (Area 3)

Tests for the use cases in `tests/team/usecases/USE_CASES.md`. Versions are recorded in `BASELINE.md`.

## One-time setup

```powershell
cd tests/team/e2e
npm.cmd install
npx.cmd playwright install chromium
```

## Run

The tests expect the documented baseline. Reset first, because a run changes the data
(for example, Bob already holds Animal Farm after UC-01 has run once):

```powershell
npm.cmd run reset      # wipes the data, restarts the stack, ends with BASELINE CLEAN
npm.cmd test           # runs all specs, writes the HTML report
npm.cmd run report     # opens the HTML report
```

## Rules

- Find records by name or email, never by loan ID.
- Copy message texts from the app (see `TEST_BASIS.md`, section 5).
- Assert the result shown and the postcondition in every test.
