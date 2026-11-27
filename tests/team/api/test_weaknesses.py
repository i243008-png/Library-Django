"""Endpoint weaknesses. Each test asserts the SAFER behaviour a requirement would expect.
xfail = the weakness is present (log it as a defect). XPASS = my prediction was wrong or it
was fixed - read the output and correct the weakness list."""
import pytest

from conftest import body, future, iso, past
from datetime import datetime, timedelta, timezone


@pytest.mark.weakness
@pytest.mark.xfail(reason="W1: API accepts a due date in the past (loan is overdue at birth)", strict=False)
def test_w1_due_date_in_the_past_is_rejected(world):
    book = world.book(2)
    assert world.lend("bob", book, due=past(5)).status_code == 400


@pytest.mark.weakness
@pytest.mark.xfail(reason="W2: API has no maximum loan period (desk form limits it to 30 days)", strict=False)
def test_w2_due_date_years_away_is_rejected(world):
    book = world.book(2)
    assert world.lend("bob", book, due=future(365 * 5)).status_code == 400


@pytest.mark.weakness
@pytest.mark.xfail(reason="W3: a return time before the loan was created is accepted", strict=False)
def test_w3_return_before_loan_start_is_rejected(world):
    book = world.book(2)
    loan = body(world.lend("bob", book))["id"]
    early = iso(datetime.now(timezone.utc) - timedelta(days=30))
    assert world.lib.patch(f"/api/v1/order/{loan}/", {"end_at": early}).status_code == 400


@pytest.mark.weakness
@pytest.mark.xfail(reason="W4: reopen with no copy answers 400 {book:...}, lending answers 409 {code}", strict=False)
def test_w4_reopen_refusal_uses_the_same_error_style_as_lending(world):
    book = world.book(1)
    first = body(world.lend("bob", book))["id"]
    world.close(first)
    world.lend("alice", book)
    r = world.lib.patch(f"/api/v1/order/{first}/", {"end_at": None})
    assert r.status_code == 409 and body(r).get("code") == "no_copy_available"
