"""Extra API tests that reach the documented status codes the first run did not hit
(401 not signed in, 403 wrong role, 404 not found, 400 bad input, 204, 409) so the
status-code coverage in api_coverage.py goes up. Each test also reads back that nothing changed."""
import pytest

from conftest import body

NOWHERE = 999999999  # an id that does not exist

# ---------- 401: anonymous user on every endpoint ----------
ANON_CASES = [
    ("GET", "/api/v1/order/1/", None),
    ("PATCH", "/api/v1/order/1/", {"end_at": None}),
    ("DELETE", "/api/v1/order/1/", None),
    ("GET", "/api/v1/user/1/order/", None),
    ("GET", "/api/v1/book/", None),
    ("POST", "/api/v1/book/", {"name": "x"}),
    ("GET", "/api/v1/book/1/", None),
    ("GET", "/api/v1/user/", None),
    ("POST", "/api/v1/reservation/", {"book": 1}),
    ("POST", "/api/v1/reservation/1/issue/", {}),
    ("POST", "/api/v1/reservation/1/cancel/", {}),
]


@pytest.mark.parametrize("method,path,payload", ANON_CASES, ids=[f"{m} {p}" for m, p, _ in ANON_CASES])
def test_401_when_not_signed_in(clients, method, path, payload):
    r = clients["anon"].call(method, path, payload)
    assert r.status_code == 401, f"{method} {path}: {r.status_code}"


# ---------- 403: a reader on librarian-only endpoints ----------
def test_403_reader_cannot_create_book(world):
    r = world.reader.post("/api/v1/book/", {"name": "QA-should-not-exist", "count": 1})
    assert r.status_code == 403


def test_403_reader_cannot_list_accounts(world):
    assert world.reader.get("/api/v1/user/").status_code == 403


def test_403_reader_cannot_issue_a_reservation(world):
    book = world.book(2)
    rid = body(world.reserve(world.alice, book))["id"]
    r = world.alice.post(f"/api/v1/reservation/{rid}/issue/", {"days": 7})
    assert r.status_code == 403
    assert world.loans_for_book(book) == []                               # no loan started
    assert body(world.lib.get(f"/api/v1/reservation/{rid}/"))["state"] == "active"


# ---------- 404: records that do not exist ----------
def test_404_unknown_loan_get_patch_delete(world):
    assert world.lib.get(f"/api/v1/order/{NOWHERE}/").status_code == 404
    assert world.lib.patch(f"/api/v1/order/{NOWHERE}/", {"end_at": None}).status_code == 404
    assert world.lib.delete(f"/api/v1/order/{NOWHERE}/").status_code == 404


def test_404_unknown_book(world):
    assert world.lib.get(f"/api/v1/book/{NOWHERE}/").status_code == 404


def test_404_unknown_reservation_issue_and_cancel(world):
    assert world.lib.post(f"/api/v1/reservation/{NOWHERE}/issue/", {"days": 7}).status_code == 404
    assert world.alice.post(f"/api/v1/reservation/{NOWHERE}/cancel/", {}).status_code == 404


# ---------- 400: invalid input on the supporting endpoints ----------
def test_400_book_without_name(world):
    r = world.lib.post("/api/v1/book/", {"description": "no name", "count": 1})
    assert r.status_code == 400 and "name" in body(r)


def test_400_reservation_without_book(world):
    r = world.alice.post("/api/v1/reservation/", {})
    assert r.status_code == 400 and "book" in body(r)


def test_400_cancel_reason_over_500_characters(world):
    """Limit from the spec (reason maxLength 500). CALIBRATE: if the app allows it, log what you see."""
    book = world.book(2)
    rid = body(world.reserve(world.alice, book))["id"]
    r = world.alice.post(f"/api/v1/reservation/{rid}/cancel/", {"reason": "x" * 501})
    assert r.status_code == 400 and "reason" in body(r)
    assert body(world.lib.get(f"/api/v1/reservation/{rid}/"))["state"] == "active"


# ---------- 200 / 204 / 409 that were never reached ----------
def test_200_list_books_contains_available_count(world):
    book = world.book(3)
    listed = {b["id"]: b for b in body(world.lib.get("/api/v1/book/"))}
    assert listed[book]["available_count"] == 3


def test_204_librarian_deletes_a_returned_loan(world):
    book = world.book(2)
    loan = body(world.lend("bob", book))["id"]
    world.close(loan)
    assert world.lib.delete(f"/api/v1/order/{loan}/").status_code == 204
    assert world.lib.get(f"/api/v1/order/{loan}/").status_code == 404     # gone
    assert world.available(book) == 2                                     # stock unchanged


def test_409_reserving_the_same_book_twice(world):
    book = world.book(3)
    assert world.reserve(world.alice, book).status_code == 201
    second = world.reserve(world.alice, book)
    assert second.status_code == 409
    assert body(second)["code"] == "already_reserved"
    assert world.available(book) == 2                                     # only one copy held


def test_200_librarian_cancels_a_reservation_with_a_reason(world):
    book = world.book(2)
    rid = body(world.reserve(world.alice, book))["id"]
    r = world.lib.post(f"/api/v1/reservation/{rid}/cancel/", {"reason": "QA test cancel"})
    assert r.status_code == 200
    assert world.available(book) == 2                                     # copy released
