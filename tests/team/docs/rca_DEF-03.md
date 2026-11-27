# Root cause analysis - DEF-03: API accepts a due date in the past
Defect: GitHub issue #11   Severity: Medium   Requirement: FR-B7   Risk id: TBD

## 5 Whys
1. Why was a loan with a due date in the past created? -> The API accepted plated_end_at without checking it against today's date.
2. Why was it not checked? -> The order serializer only checks that it is a valid date and time.
3. Why no further rule? -> The 1 to 30 day limit exists only in the desk form and the reservation-issue endpoint, not in the order API.
4. Why in only some places? -> The same business rule was written separately in each place instead of once in shared code.
5. Why was that not caught? -> ROOT CAUSE: the loan-period rule was never specified for the API and no test covered that path.

## Actions
| Type | Action | Owner | Due | Verified by |
|---|---|---|---|---|
| Corrective | Reject a past plated_end_at (and one over 30 days) in the order serializer | team | before release | test_w1 passes |
| Preventive | Put the loan-period rule in one shared function used by the form and the API, and write it in the spec | Umm-e-Sulaim | before release | Regenerated tests cover the same limits |
