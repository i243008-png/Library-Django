"""Playwright tests for UC-05 (Reserve a book, librarian issues it) and UC-06 (Correct a loan on
the Edit screen), written by Umm-e-Sulaim. Every flow asserts the message shown AND the
postcondition (available copies / loan state read through the API).
Run from the repo root, app running:
    pytest tests/team/usecases/test_uc05_uc06.py --headed --slowmo 300 -q
    pytest tests/team/usecases/test_uc05_uc06.py --html=uc05_uc06_report.html --self-contained-html -q
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from conftest import ACCOUNTS, BASE, Api, World, body, iso, past  # noqa: E402

BOB = "Bob Williams"


@pytest.fixture()
def world():
    lib, reader, alice, bob = Api("librarian"), Api("reader"), Api("alice"), Api("bob")
    w = World(lib, reader, alice, bob)
    yield w
    w.cleanup()


def named_book(world, count=5):
    book_id = world.book(count)
    return book_id, body(world.lib.get(f"/api/v1/book/{book_id}/"))["name"]


def sign_in(page: Page, role: str):
    email, password = ACCOUNTS[role]
    page.goto(f"{BASE}/authentication/login/")
    page.get_by_label("Email Address").fill(email)
    page.get_by_label("Password").fill(password)
    page.locator("main form button[type=submit]").click()
    page.wait_for_url(f"{BASE}/")


@pytest.fixture()
def librarian_page(browser: Browser):
    ctx = browser.new_context()
    page = ctx.new_page()
    sign_in(page, "librarian")
    yield page
    ctx.close()


def status(page: Page):
    return page.get_by_role("status")


def dt(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def reserve_as_bob(page: Page, book_id: int, name: str):
    page.goto(f"{BASE}/book/{book_id}/")
    page.get_by_role("button", name=re.compile(r"Reserve for \d+ Hours?")).click()
    expect(status(page)).to_contain_text(f"Reserved “{name}”. Collect it from a librarian before ")


def issue_at_desk(lib: Page, name: str, days: str = "14"):
    lib.goto(f"{BASE}/order/reservations/desk/")
    lib.get_by_role("link", name=re.compile(rf"^Issue.*{re.escape(name)}")).first.click()
    expect(lib.get_by_role("heading", name="Issue Reservation")).to_be_visible()
    lib.get_by_label("Loan Duration (Days)").fill(days)
    lib.get_by_role("button", name="Issue Book").click()


# =========================== UC-05 Reserve a book and have it issued ===========================
def test_uc05_main_reserve_then_issue(page: Page, librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    sign_in(page, "bob")
    reserve_as_bob(page, book_id, name)
    assert world.available(book_id) == 4                                    # reservation holds a copy
    issue_at_desk(librarian_page, name, "14")
    expect(status(librarian_page)).to_contain_text(f"Issued “{name}” to {BOB} as loan #")
    loans = world.loans_for_book(book_id)
    assert len(loans) == 1 and loans[0]["end_at"] is None                   # one open loan
    assert world.available(book_id) == 4                                    # the held copy became the loan


def test_uc05_af1_issue_for_30_days(page: Page, librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    sign_in(page, "bob")
    reserve_as_bob(page, book_id, name)
    issue_at_desk(librarian_page, name, "30")
    expect(status(librarian_page)).to_contain_text(f"Issued “{name}” to {BOB} as loan #")
    loan = world.loans_for_book(book_id)[0]
    assert abs((dt(loan["plated_end_at"]) - dt(loan["created_at"])) - timedelta(days=30)) < timedelta(minutes=5)


def test_uc05_af2_issue_for_1_day(page: Page, librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    sign_in(page, "bob")
    reserve_as_bob(page, book_id, name)
    issue_at_desk(librarian_page, name, "1")
    expect(status(librarian_page)).to_contain_text(f"Issued “{name}” to {BOB} as loan #")
    loan = world.loans_for_book(book_id)[0]
    assert abs((dt(loan["plated_end_at"]) - dt(loan["created_at"])) - timedelta(days=1)) < timedelta(minutes=5)


def test_uc05_af3_reader_cancels_own_reservation(page: Page, world):
    book_id, name = named_book(world, 5)
    sign_in(page, "bob")
    reserve_as_bob(page, book_id, name)
    assert world.available(book_id) == 4
    page.goto(f"{BASE}/order/reservations/")
    page.get_by_role("link", name=re.compile(rf"Cancel.*{re.escape(name)}")).first.click()
    page.get_by_role("button", name="Yes, Cancel Reservation").click()
    expect(status(page)).to_contain_text(f"Cancelled your reservation of “{name}”.")
    assert world.available(book_id) == 5                                    # copy is free again
    assert world.loans_for_book(book_id) == []


def test_uc05_ef1_book_already_reserved(page: Page, world):
    book_id, name = named_book(world, 5)
    assert world.reserve(world.bob, book_id).status_code == 201
    sign_in(page, "bob")
    page.goto(f"{BASE}/book/{book_id}/")
    expect(page.locator("main")).to_contain_text(f"You already reserved “{name}”. Collect it from a librarian before ")
    expect(page.get_by_role("button", name=re.compile(r"Reserve for"))).to_have_count(0)
    assert world.available(book_id) == 4                                    # only one copy held


def test_uc05_ef2_reader_has_an_overdue_loan(page: Page, world):
    overdue_id, overdue_name = named_book(world, 5)
    assert world.lend("bob", overdue_id, due=past(5)).status_code == 201     # bob is now overdue
    book_id, name = named_book(world, 5)
    sign_in(page, "bob")
    page.goto(f"{BASE}/book/{book_id}/")
    expect(page.locator("main")).to_contain_text(f"“{overdue_name}” was due on ")
    expect(page.locator("main")).to_contain_text("Return it before reserving or borrowing another book.")
    expect(page.get_by_role("button", name=re.compile(r"Reserve for"))).to_have_count(0)
    assert world.available(book_id) == 5                                    # nothing reserved


def test_uc05_ef3_no_copy_available(page: Page, world):
    book_id, name = named_book(world, 1)
    assert world.lend("alice", book_id).status_code == 201                   # takes the only copy
    sign_in(page, "bob")
    page.goto(f"{BASE}/book/{book_id}/")
    expect(page.locator("main")).to_contain_text(f"No copy of “{name}” is available right now.")
    expect(page.get_by_role("button", name=re.compile(r"Reserve for"))).to_have_count(0)
    assert world.available(book_id) == 0


def test_uc05_ef4_reservation_already_issued(librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    rid = body(world.reserve(world.bob, book_id))["id"]
    issued = world.lib.post(f"/api/v1/reservation/{rid}/issue/", {"days": 7})
    assert issued.status_code == 201
    world.open_loans.append(body(issued)["loan"]["id"])
    librarian_page.goto(f"{BASE}/order/reservations/{rid}/issue/")
    expect(librarian_page.locator("main")).to_contain_text("This reservation was already issued as loan #")
    expect(librarian_page.get_by_role("button", name="Issue Book")).to_have_count(0)
    assert len(world.loans_for_book(book_id)) == 1                           # no second loan


# =========================== UC-06 Correct a loan on the Edit screen ===========================
def open_edit(page: Page, loan_id: int):
    page.goto(f"{BASE}/order/update/{loan_id}/")
    expect(page.get_by_role("heading", name=f"Edit Order #{loan_id}")).to_be_visible()


def local_value(days: int) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M")


def test_uc06_main_extend_planned_return(librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    loan = body(world.lend("bob", book_id))["id"]
    before = dt(body(world.lib.get(f"/api/v1/order/{loan}/"))["plated_end_at"])
    open_edit(librarian_page, loan)
    planned = librarian_page.get_by_label("Planned Return Date & Time")
    # the box counts in seconds from the loan's own time, so keep its seconds: shift by 20 days
    new_value = (datetime.fromisoformat(planned.input_value()) + timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%S")
    planned.fill(new_value)
    assert planned.evaluate("e => e.validity.valid"), planned.evaluate("e => e.validationMessage")
    with librarian_page.expect_navigation(url=re.compile(r"/order/all/"), timeout=15000):
        librarian_page.get_by_role("button", name="Save Order Changes").click()
    expect(status(librarian_page)).to_contain_text(f"Changes to loan #{loan} saved.")
    saved = body(world.lib.get(f"/api/v1/order/{loan}/"))
    assert abs(dt(saved["plated_end_at"]) - (before + timedelta(days=20))) < timedelta(hours=1)  # due date moved 20 days
    assert saved["end_at"] is None and world.available(book_id) == 4        # still open, stock unchanged


def test_uc06_af1_record_the_return_on_the_edit_screen(librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    loan = body(world.lend("bob", book_id))["id"]
    open_edit(librarian_page, loan)
    librarian_page.get_by_label("Actual Return Date & Time").fill(local_value(0))
    librarian_page.get_by_role("button", name="Save Order Changes").click()
    expect(status(librarian_page)).to_contain_text(f"Changes to loan #{loan} saved.")
    assert body(world.lib.get(f"/api/v1/order/{loan}/"))["end_at"] is not None
    assert world.available(book_id) == 5                                    # copy is back


def test_uc06_af2_reopen_a_returned_loan_when_a_copy_is_free(librarian_page: Page, world):
    book_id, name = named_book(world, 1)
    loan = body(world.lend("bob", book_id))["id"]
    world.close(loan)
    assert world.available(book_id) == 1
    open_edit(librarian_page, loan)
    librarian_page.get_by_label("Actual Return Date & Time").fill("")
    librarian_page.get_by_role("button", name="Save Order Changes").click()
    expect(status(librarian_page)).to_contain_text(f"Changes to loan #{loan} saved.")
    assert body(world.lib.get(f"/api/v1/order/{loan}/"))["end_at"] is None   # open again
    assert world.available(book_id) == 0


def test_uc06_af3_cancel_leaves_the_loan_unchanged(librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    loan = body(world.lend("bob", book_id))["id"]
    before = body(world.lib.get(f"/api/v1/order/{loan}/"))
    open_edit(librarian_page, loan)
    librarian_page.get_by_label("Planned Return Date & Time").fill(local_value(25))
    librarian_page.get_by_role("link", name="Cancel").click()
    expect(librarian_page).to_have_url(re.compile(r"/order/all/"))
    assert body(world.lib.get(f"/api/v1/order/{loan}/")) == before
    assert world.available(book_id) == 4


def test_uc06_ef1_reopen_refused_when_no_copy_is_free(librarian_page: Page, world):
    book_id, name = named_book(world, 1)
    first = body(world.lend("bob", book_id))["id"]
    world.close(first)
    assert world.lend("alice", book_id).status_code == 201                   # takes the only copy
    open_edit(librarian_page, first)
    librarian_page.get_by_label("Actual Return Date & Time").fill("")
    librarian_page.get_by_role("button", name="Save Order Changes").click()
    expect(librarian_page.locator("main")).to_contain_text("No copies of this book are currently available.")
    expect(librarian_page).to_have_url(re.compile(rf"/order/update/{first}/"))   # stayed on the form
    assert body(world.lib.get(f"/api/v1/order/{first}/"))["end_at"] is not None  # still returned
    assert world.available(book_id) == 0


def test_uc06_ef2_planned_return_cannot_be_empty(librarian_page: Page, world):
    book_id, name = named_book(world, 5)
    loan = body(world.lend("bob", book_id))["id"]
    before = body(world.lib.get(f"/api/v1/order/{loan}/"))
    open_edit(librarian_page, loan)
    field = librarian_page.get_by_label("Planned Return Date & Time")
    field.fill("")
    librarian_page.get_by_role("button", name="Save Order Changes").click()
    expect(librarian_page).to_have_url(re.compile(rf"/order/update/{loan}/"))
    assert field.evaluate("e => e.validity.valueMissing") is True            # browser blocks the submit
    assert body(world.lib.get(f"/api/v1/order/{loan}/")) == before


def test_uc06_ef3_a_reader_cannot_open_the_edit_screen(page: Page, world):
    book_id, name = named_book(world, 5)
    loan = body(world.lend("bob", book_id))["id"]
    sign_in(page, "bob")
    response = page.goto(f"{BASE}/order/update/{loan}/")
    assert response.status == 404
    expect(page.get_by_role("button", name="Save Order Changes")).to_have_count(0)
    assert body(world.lib.get(f"/api/v1/order/{loan}/"))["end_at"] is None
