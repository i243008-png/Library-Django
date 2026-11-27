# Effect of changing days: max 30 -> 21 and min 1 -> 3

| Value | Before | After |
|---|---|---|
| 14.5 | reject | reject |
| -7 | - | reject  <-- CHANGED |
| -9 | reject | -  <-- CHANGED |
| 0 | reject | -  <-- CHANGED |
| 1 | accept | -  <-- CHANGED |
| 14 | accept | accept |
| 2 | accept | reject  <-- CHANGED |
| 20 | - | accept  <-- CHANGED |
| 21 | - | accept  <-- CHANGED |
| 22 | - | reject  <-- CHANGED |
| 29 | accept | -  <-- CHANGED |
| 3 | - | accept  <-- CHANGED |
| 30 | accept | -  <-- CHANGED |
| 31 | reject | reject |
| 4 | - | accept  <-- CHANGED |
| 40 | reject | -  <-- CHANGED |
| "$MISSING" | accept | accept |
| "$NULL" | reject | reject |
| "abc" | reject | reject |
