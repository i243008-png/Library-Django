# AI-use record - Umm-e-Sulaim Rana (24i-3062)
Rule: tool, purpose, output, what I checked or changed. Keep the prompts (paste or save the chat link).
**Status column: only write "Checked" after you really did the check. Do not edit evidence.**

| # | Tool | Purpose | Output received | What I checked / changed | Status |
|---|---|---|---|---|---|
| 1 | Claude | Read the Django Library Orders code and derive requirements, 4 business rules, roles | Test basis in test_plan.md section 2 | Compare every rule with order/services.py, models.py yourself; note what you changed | TO VERIFY |
| 2 | Claude | Write OpenAPI spec | tests/team/api/openapi.yaml | Open http://localhost:8000/api/docs/ and compare each path/status/field with the real app | TO VERIFY |
| 3 | Claude | Write the generator | generator/generate_cases.py | Run it, read cases.md, explain one field by hand | TO VERIFY |
| 4 | Claude | Write API tests | test_*.py | Run them, read each assertion, fix wrong expectations | TO VERIFY |
| 5 | Claude | Write test plan, estimates, templates, use cases, Playwright tests | docs/*, usecases/* | Change numbers to your real ones; run by hand once | TO VERIFY |

## Example of an output I changed or rejected (the viva asks for one)
(Write one real example here after you run the tests - e.g. "the test expected X, the app really returns Y, so I changed the assertion".)
