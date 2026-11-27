# Generated test cases (EP + 3-point BVA)


## create_order  (schema OrderCreate, 27 cases)

| ID | Field | Technique | Class | Value | Expected |
|---|---|---|---|---|---|
| create_order-01 | user | EP | valid id of an existing record | `$REAL_USER` | accept (201) |
| create_order-02 | user | EP | invalid: id of a record that does not exist | `999999999` | reject 400 |
| create_order-03 | user | EP | invalid: below minimum 1 | `0` | reject 400 |
| create_order-04 | user | EP | invalid: negative id | `-5` | reject 400 |
| create_order-05 | user | EP | invalid: text instead of a number | `abc` | reject 400 |
| create_order-06 | user | EP | invalid: decimal number | `14.5` | reject 400 |
| create_order-07 | user | EP | invalid: null | `$NULL` | reject 400 |
| create_order-08 | user | EP | invalid: field missing | `$MISSING` | reject 400 |
| create_order-09 | book | EP | valid id of an existing record | `$REAL_BOOK` | accept (201) |
| create_order-10 | book | EP | invalid: id of a record that does not exist | `999999999` | reject 400 |
| create_order-11 | book | EP | invalid: below minimum 1 | `0` | reject 400 |
| create_order-12 | book | EP | invalid: negative id | `-5` | reject 400 |
| create_order-13 | book | EP | invalid: text instead of a number | `abc` | reject 400 |
| create_order-14 | book | EP | invalid: decimal number | `14.5` | reject 400 |
| create_order-15 | book | EP | invalid: null | `$NULL` | reject 400 |
| create_order-16 | book | EP | invalid: field missing | `$MISSING` | reject 400 |
| create_order-17 | plated_end_at | EP | valid: ISO date-time | `$FUTURE_ISO` | accept (201) |
| create_order-18 | plated_end_at | EP | invalid: not a date | `not-a-date` | reject 400 |
| create_order-19 | plated_end_at | EP | invalid: impossible date | `2026-13-45T00:00:00Z` | reject 400 |
| create_order-20 | plated_end_at | EP | invalid: number instead of text | `12345` | reject 400 |
| create_order-21 | plated_end_at | EP | invalid: null | `$NULL` | reject 400 |
| create_order-22 | plated_end_at | EP | invalid: field missing | `$MISSING` | reject 400 |
| create_order-23 | end_at | EP | valid: ISO date-time | `$NULL` | accept (201) |
| create_order-24 | end_at | EP | invalid: not a date | `not-a-date` | reject 400 |
| create_order-25 | end_at | EP | invalid: impossible date | `2026-13-45T00:00:00Z` | reject 400 |
| create_order-26 | end_at | EP | invalid: number instead of text | `12345` | reject 400 |
| create_order-27 | end_at | EP | valid: field missing | `$MISSING` | accept (201) |

## return_loan  (schema OrderReturn, 6 cases)

| ID | Field | Technique | Class | Value | Expected |
|---|---|---|---|---|---|
| return_loan-01 | end_at | EP | valid: ISO date-time | `$NOW_ISO` | accept (200) |
| return_loan-02 | end_at | EP | invalid: not a date | `not-a-date` | reject 400 |
| return_loan-03 | end_at | EP | invalid: impossible date | `2026-13-45T00:00:00Z` | reject 400 |
| return_loan-04 | end_at | EP | invalid: number instead of text | `12345` | reject 400 |
| return_loan-05 | end_at | EP | valid: null | `$NULL` | accept (200) |
| return_loan-06 | end_at | EP | valid: field missing | `$MISSING` | accept (200) |

## issue_reservation  (schema IssueRequest, 13 cases)

| ID | Field | Technique | Class | Value | Expected |
|---|---|---|---|---|---|
| issue_reservation-01 | days | EP | valid: inside the range | `14` | accept (201) |
| issue_reservation-02 | days | EP | invalid: far below range | `-9` | reject 400 |
| issue_reservation-03 | days | EP | invalid: far above range | `40` | reject 400 |
| issue_reservation-04 | days | BVA | just below min (1) | `0` | reject 400 |
| issue_reservation-05 | days | BVA | at min (1) | `1` | accept (201) |
| issue_reservation-06 | days | BVA | just above min (1) | `2` | accept (201) |
| issue_reservation-07 | days | BVA | just below max (30) | `29` | accept (201) |
| issue_reservation-08 | days | BVA | at max (30) | `30` | accept (201) |
| issue_reservation-09 | days | BVA | just above max (30) | `31` | reject 400 |
| issue_reservation-10 | days | EP | invalid: text instead of a number | `abc` | reject 400 |
| issue_reservation-11 | days | EP | invalid: decimal number | `14.5` | reject 400 |
| issue_reservation-12 | days | EP | invalid: null | `$NULL` | reject 400 |
| issue_reservation-13 | days | EP | valid: field missing (default used) | `$MISSING` | accept (201) |

**Total cases: 46**
