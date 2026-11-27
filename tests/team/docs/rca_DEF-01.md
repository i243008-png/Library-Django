# Root cause analysis - DEF-01: Borrow request without "book" returns 500 instead of 400
Defect: GitHub issue #9   Severity: High   Requirement: FR-B7   Risk id: TBD

## 5 Whys
1. Why did the request fail with a server error? -> The code read validated_data["book"] and "book" was not in it (KeyError).
2. Why was "book" not in it? -> The request had no "book" and validation did not reject it.
3. Why did validation not reject it? -> The API treats "book" as optional.
4. Why is it optional? -> The model field Order.book has default=None, and Django REST Framework treats a field with a default as not required.
5. Why was that not caught? -> ROOT CAUSE: a default was added to the model field without making "book" required in the API, and no upstream test sends a request with a field missing.

## Actions
| Type | Action | Owner | Due | Verified by |
|---|---|---|---|---|
| Corrective | Make "book" required in the order serializer so a missing book returns 400 | team | before release | test_borrow_create_order[create_order-16] passes |
| Preventive | Keep the generated "field missing" test for every required field in the CI pipeline; review model defaults whenever a serializer changes | Umm-e-Sulaim | before release | CI fails if any required-field test fails |
