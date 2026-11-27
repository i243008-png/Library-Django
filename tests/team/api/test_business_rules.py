"""Business rules, state changes, roles, repeated requests and read-backs (not generated)."""
import threading

import pytest

from conftest import Api, body, future, iso, past
from datetime import datetime, timezone


# ---------- BR1: boundary - a copy can only be lent while available_count >= 1 ----------
@pytest.mark.rule
@pytest.mark.parametrize("copies", [0, 1, 2])
def test_br1_availability_boundary(world, copies):
    """Lend `copies` times (below/at the limit) then once more (just above): refused."""
    readers = ["bob", "alice", "reader"]
    book = world.book(copies)
    for i in range(copies):
        r = world.lend(readers[i], book)
        assert r.status_code == 201, r.text
        assert world.available(book) == copies - i - 1
    over = world.lend(readers[copies], book)
    assert over.status_code == 409
    assert body(over)["code"] == "no_copy_available"
    assert world.available(book) == 0                     # rejection changed nothing
    assert len(world.loans_for_book(book)) == copies


# ---------- BR2: decision table - overdue loan (A) and already has this book (B) ----------
@pytest.mark.rule
@pytest.mark.parametrize("overdue,on_loan,expected", [
    (False, False, 201),                  # R1: both false  -> lent
    (True, False, "overdue_loan"),        # R2: A only      -> refused
    (False, True, "already_on_loan"),     # R3: B only      -> refused
    (True, True, "overdue_loan"),         # R4: both true   -> refused, overdue is checked first
], ids=["F-F", "T-F", "F-T", "T-T"])
def test_br2_decision_table(world, overdue, on_loan, expected):
    x, y = world.book(5), world.book(5)
    first = world.lend("bob", x, due=past() if overdue else future())
    assert first.status_code == 201, first.text
    target = x if on_loan else y
    loans_before = len(world.loans_for_book(target))
    avail_before = world.available(target)
    r = world.lend("bob", target)
    if expected == 201:
        assert r.status_code == 201
        assert world.available(target) == avail_before - 1
    else:
        assert r.status_code == 409
        assert body(r)["code"] == expected
        assert len(world.loans_for_book(target)) == loans_before
        assert world.available(target) == avail_before


# ---------- BR3: state change - open -> returned -> (reopen) ----------
@pytest.mark.rule
def test_br3_open_to_returned(world):
    book = world.book(3)
    loan = body(world.lend("bob", book))["id"]
    assert world.available(book) == 2
    r = world.close(loan)
    assert r.status_code == 200 and body(r)["end_at"] is not None
    assert world.available(book) == 3


@pytest.mark.rule
def test_br3_returned_to_returned_changes_nothing_more(world):
    book = world.book(3)
    loan = body(world.lend("bob", book))["id"]
    assert world.close(loan).status_code == 200
    again = world.close(loan)                              # repeated return
    assert again.status_code == 200
    assert world.available(book) == 3                      # stock not increased twice
    assert len(world.loans_for_book(book)) == 1            # no duplicate loan


@pytest.mark.rule
def test_br3_reopen_allowed_when_a_copy_is_free(world):
    book = world.book(1)
    loan = body(world.lend("bob", book))["id"]
    world.close(loan)
    r = world.lib.patch(f"/api/v1/order/{loan}/", {"end_at": None})
    assert r.status_code == 200 and body(r)["end_at"] is None
    assert world.available(book) == 0


@pytest.mark.rule
def test_br3_reopen_refused_when_no_copy_is_free(world):
    """Disallowed transition returned -> open: the only copy is on loan to someone else."""
    book = world.book(1)
    first = body(world.lend("bob", book))["id"]
    world.close(first)
    assert world.lend("alice", book).status_code == 201     # takes the single copy
    r = world.lib.patch(f"/api/v1/order/{first}/", {"end_at": None})
    assert r.status_code == 400 and "book" in body(r)
    assert body(world.lib.get(f"/api/v1/order/{first}/"))["end_at"] is not None  # still returned
    assert world.available(book) == 0


# ---------- BR4: roles - only librarians change loans; readers see only their own ----------
@pytest.mark.rule
def test_br4_anonymous_is_refused(clients):
    assert clients["anon"].get("/api/v1/order/").status_code == 401
    assert clients["anon"].post("/api/v1/order/", {}).status_code == 401


@pytest.mark.rule
def test_br4_reader_cannot_lend(world):
    book = world.book(2)
    before = world.available(book)
    r = world.reader.post("/api/v1/order/", {"user": world.uid("reader"), "book": book, "plated_end_at": future()})
    assert r.status_code == 403
    assert world.available(book) == before and world.loans_for_book(book) == []


@pytest.mark.rule
def test_br4_reader_cannot_return_or_delete(world):
    book = world.book(2)
    loan = body(world.lend("bob", book))["id"]
    assert world.bob.patch(f"/api/v1/order/{loan}/", {"end_at": iso(datetime.now(timezone.utc))}).status_code == 403
    assert world.bob.delete(f"/api/v1/order/{loan}/").status_code == 403
    assert body(world.lib.get(f"/api/v1/order/{loan}/"))["end_at"] is None   # unchanged
    assert world.available(book) == 1


@pytest.mark.rule
def test_br4_reader_sees_only_own_loans(world):
    book = world.book(3)
    bob_loan = body(world.lend("bob", book))["id"]
    alice_loan = body(world.lend("alice", book))["id"]
    mine = [o["id"] for o in body(world.bob.get("/api/v1/order/"))]
    assert bob_loan in mine and alice_loan not in mine
    assert world.bob.get(f"/api/v1/order/{alice_loan}/").status_code == 404
    assert world.bob.get(f"/api/v1/user/{world.uid('alice')}/order/").status_code == 404
    assert world.bob.get(f"/api/v1/user/{world.uid('bob')}/order/").status_code == 200
    everyone = [o["id"] for o in body(world.lib.get("/api/v1/order/"))]
    assert bob_loan in everyone and alice_loan in everyone


# ---------- Repeated requests: no duplicates ----------
@pytest.mark.rule
def test_repeat_borrow_creates_one_loan(world):
    book = world.book(5)
    assert world.lend("bob", book).status_code == 201
    second = world.lend("bob", book)
    assert second.status_code == 409 and body(second)["code"] == "already_on_loan"
    assert len(world.loans_for_book(book)) == 1
    assert world.available(book) == 4


@pytest.mark.rule
def test_simultaneous_duplicate_borrow_creates_one_loan(world):
    book = world.book(5)
    payload = {"user": world.uid("bob"), "book": book, "plated_end_at": future()}
    sessions = [Api("librarian"), Api("librarian")]
    barrier, results = threading.Barrier(2), []

    def go(api):
        barrier.wait()
        results.append(api.post("/api/v1/order/", payload))

    threads = [threading.Thread(target=go, args=(s,)) for s in sessions]
    [t.start() for t in threads]
    [t.join() for t in threads]
    for r in results:
        if r.status_code == 201:
            world.open_loans.append(body(r)["id"])
    assert sorted(r.status_code for r in results) == [201, 409]
    assert len(world.loans_for_book(book)) == 1
    assert world.available(book) == 4


@pytest.mark.rule
def test_repeat_issue_reservation_starts_one_loan(world):
    book = world.book(5)
    rid = body(world.reserve(world.alice, book))["id"]
    first = world.lib.post(f"/api/v1/reservation/{rid}/issue/", {"days": 7})
    assert first.status_code == 201
    world.open_loans.append(body(first)["loan"]["id"])
    second = world.lib.post(f"/api/v1/reservation/{rid}/issue/", {"days": 7})
    assert second.status_code == 409 and body(second)["code"] == "already_issued"
    assert body(second)["loan"] == body(first)["loan"]["id"]
    assert len(world.loans_for_book(book)) == 1


# ---------- Cross-workflow read-back: borrow and return share available_count ----------
@pytest.mark.rule
def test_borrow_then_return_read_back(world):
    book = world.book(2)
    uid = world.uid("bob")
    assert world.available(book) == 2
    loan = body(world.lend("bob", book))
    assert world.available(book) == 1
    listed = {o["id"]: o for o in body(world.lib.get(f"/api/v1/user/{uid}/order/"))}
    assert listed[loan["id"]]["end_at"] is None
    assert loan["id"] in [o["id"] for o in body(world.bob.get("/api/v1/order/"))]
    world.close(loan["id"])
    assert world.available(book) == 2
    listed = {o["id"]: o for o in body(world.lib.get(f"/api/v1/user/{uid}/order/"))}
    assert listed[loan["id"]]["end_at"] is not None
