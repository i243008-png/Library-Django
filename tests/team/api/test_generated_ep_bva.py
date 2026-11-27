"""API tests driven by the generator output (results/cases.json): EP + 3-point BVA.

One field is changed per test, so one invalid value per test. After every call the shared
record (the book's available_count) and the loan list are read back.
Run `python generator/generate_cases.py` first so results/cases.json is current.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import body, future, iso

CASES = json.loads((Path(__file__).parent / "results" / "cases.json").read_text(encoding="utf-8"))


def params(target):
    return [pytest.param(c, id=c["id"]) for c in CASES[target]["cases"]]


def resolve(value, ctx):
    table = {"$REAL_USER": ctx.get("user"), "$REAL_BOOK": ctx.get("book"), "$FUTURE_ISO": future(),
             "$NOW_ISO": iso(datetime.now(timezone.utc)), "$NULL": None}
    return table.get(value, value) if isinstance(value, str) else value


def build_payload(target, case, ctx):
    payload = {f: resolve(v, ctx) for f, v in CASES[target]["baseline"].items()}
    if case["value"] == "$MISSING":
        payload.pop(case["field"], None)
    else:
        payload[case["field"]] = resolve(case["value"], ctx)
    return payload


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@pytest.mark.generated
@pytest.mark.parametrize("case", params("create_order"))
def test_borrow_create_order(world, case):
    book = world.book(5)
    ctx = {"user": world.uid("bob"), "book": book}
    before, loans_before = world.available(book), len(world.loans_for_book(book))
    payload = build_payload("create_order", case, ctx)
    r = world.lib.post("/api/v1/order/", payload)
    if r.status_code == 201:
        world.open_loans.append(body(r)["id"])
    assert r.status_code == case["expect_status"], f"{case['class']}: {r.status_code} {r.text[:200]}"
    if case["valid"]:
        opened = payload.get("end_at") is None
        assert world.available(book) == before - (1 if opened else 0)
        assert len(world.loans_for_book(book)) == loans_before + 1
    else:
        assert case["field"] in body(r), f"error should name '{case['field']}', got {r.text[:200]}"
        assert world.available(book) == before          # nothing consumed
        assert len(world.loans_for_book(book)) == loans_before  # no loan written


@pytest.mark.generated
@pytest.mark.parametrize("case", params("return_loan"))
def test_return_patch_end_at(world, case):
    book = world.book(5)
    loan = body(world.lend("bob", book))["id"]
    before = world.available(book)                       # one copy already out
    payload = build_payload("return_loan", case, {})
    r = world.lib.patch(f"/api/v1/order/{loan}/", payload)
    assert r.status_code == case["expect_status"], f"{case['class']}: {r.status_code} {r.text[:200]}"
    state = body(world.lib.get(f"/api/v1/order/{loan}/"))
    if case["valid"]:
        returned = payload.get("end_at") is not None
        assert (state["end_at"] is not None) == returned
        assert world.available(book) == before + (1 if returned else 0)
    else:
        assert "end_at" in body(r)
        assert state["end_at"] is None                    # still on loan
        assert world.available(book) == before


@pytest.mark.generated
@pytest.mark.parametrize("case", params("issue_reservation"))
def test_issue_reservation_days(world, case):
    book = world.book(5)
    res = world.reserve(world.alice, book)
    assert res.status_code == 201, res.text
    rid = body(res)["id"]
    held = world.available(book)                          # the reservation already holds a copy
    payload = {} if case["value"] == "$MISSING" else {"days": resolve(case["value"], {})}
    r = world.lib.post(f"/api/v1/reservation/{rid}/issue/", payload)
    assert r.status_code == case["expect_status"], f"{case['class']}: {r.status_code} {r.text[:200]}"
    if case["valid"]:
        loan = body(r)["loan"]
        world.open_loans.append(loan["id"])
        days = 14 if case["value"] == "$MISSING" else case["value"]
        length = parse(loan["plated_end_at"]) - parse(loan["created_at"])
        assert abs(length - timedelta(days=days)) < timedelta(minutes=5)
        assert world.available(book) == held              # the held copy became the loan
        assert body(r)["reservation"]["state"] == "issued"
    else:
        assert "days" in body(r)
        assert world.loans_for_book(book) == []           # no loan started
        assert world.available(book) == held
        assert body(world.lib.get(f"/api/v1/reservation/{rid}/"))["state"] == "active"
