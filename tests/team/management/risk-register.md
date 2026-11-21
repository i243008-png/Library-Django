###### Risk scales

Likelihood: how likely is it to happen?



Number	Meaning

1	Rare

2	Unlikely

3	Possible

4	Likely

5	Almost certain



Impact: how bad is it if it happens?



Number	Meaning

1	Cosmetic

2	Minor annoyance

3	A user can't finish a task

4	Wrong data for one user

5	Wrong data for everyone, or a security hole



Score = likelihood × impact. For example R1 below is 3 × 5 = 15.



Score	Level	How hard to test

15 to 25	High	Several techniques (MC/DC, boundaries, mutation)

8 to 14	Medium	Equivalence classes and boundary values

1 to 7	Low	One or two checks
1. Product risks
ID	What could go wrong	L	I	Score	Why these numbers	How we test it	Evidence so far


---

R1	A loan starts when no copy is free, so the shared copy count goes wrong	3	5	15 High	Many code paths touch it (L3). It corrupts data for everyone (I5)	MC/DC on Order.save(), boundary 0 and 1 copy, API tests, mutation	OrderSaveCopyRuleTests, test\_br2\_\*

R2	A reader with an overdue loan can still borrow	3	3	9 Medium	The rule is a two-condition decision (L3). One reader gets a wrong result (I3)	Decision table, due-date boundary	test\_br3\_\* (7 tests)

R3	A repeated request creates a duplicate loan	3	4	12 Medium	Users double-click and retry (L3). It gives wrong data for one reader (I4)	Repeat-request test and read-back	test\_a\_repeated\_lend\_of\_the\_same\_book\_creates\_no\_duplicate

R4	A return does not release the copy, or a double return damages the count	2	5	10 Medium	Code already guards it (L2). It damages the shared count (I5)	State-transition tests, read-back	test\_closing\_a\_loan\_releases\_the\_copy, test\_changing\_the\_return\_time\_...

R5	The 1 to 30 day loan limit can be bypassed (suspected: only the forms check it)	4	3	12 Medium	The code reading suggests a gap (L4). A wrong due date is not severe (I3)	3-point boundary tests through the API	None yet. Umm-e-Sulaim's API tests

R6	A reader does librarian actions	2	5	10 Medium	Role checks exist (L2). A security hole (I5)	Access matrix, allowed and denied checks	test\_only\_a\_librarian\_can\_lend (service level), Maha's access checks later

R7	Two lends of the last copy at the same moment	2	5	10 Medium	The code uses locks (L2). It would damage the count (I5)	Repeated runs, lock and race test	One mocked race test, StartLoanRaceTests. Real concurrency not yet tested

R8	Reopening a returned loan when no copy is free	2	4	8 Medium	A rare admin action (L2). Wrong data for one reader (I4)	State-transition tests	test\_reopening\_a\_returned\_loan\_\*


2\. Project risks
ID	What could go wrong	L	I	Score	What we do about it
---

P1	One member is busy or the work is uneven	3	4	12	Cross-review pull requests, weekly progress report, clear ownership

P2	The environment is slow or breaks (50-minute first build, the static files error)	4	3	12	Reset script, written commands, known-issues list

P3	The upstream repo changes and breaks our baseline	2	4	8	Fixed baseline commit, no git pull from upstream


3. Risk matrix 5x5

---

L \\ I	1	2	3	4	5

5					

4			R5, P2		

3			R2	R3, P1	R1

2				R8, P3	R4, R6, R7

1		


4\. Exit criteria

---

ID	Rule	Linked to	Target	Where the value comes from

E1	Branch coverage of the in-scope loan code	R1, R4	100%, every uncovered line justified	Coverage report

E2	Mutation score on the rule code	R1, R2, R5	Leave the number blank for now	mutmut

E3	Open critical or high defects in lend and return	R1, R3, R5	0	GitHub Issues

E4	Every high or medium risk has at least one passing test	all	100%	Traceability matrix			

