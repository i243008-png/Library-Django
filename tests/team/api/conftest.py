"""Shared helpers for the API tests: login, CSRF, call logging, test-data builders.

The app uses Django SESSION login, so every client first opens the login page (to get the
CSRF cookie), posts the login form, and then sends the X-CSRFToken header on changes.
"""
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

BASE = os.getenv("LIBRARY_BASE_URL", "http://localhost:8000").rstrip("/")
# These are the demo accounts the repo seeds itself (seed_db.py). Override with env vars.
ACCOUNTS = {
    "librarian": (os.getenv("LIB_EMAIL", "librarian@library.com"), os.getenv("LIB_PASSWORD", "admin123password")),
    "reader": (os.getenv("READER_EMAIL", "reader@library.com"), os.getenv("READER_PASSWORD", "reader123password")),
    "alice": ("alice@library.com", os.getenv("ALICE_PASSWORD", "alice123password")),
    "bob": ("bob@library.com", os.getenv("BOB_PASSWORD", "bob123password")),
}
HERE = Path(__file__).resolve().parent
CALL_LOG = HERE / "results" / "api_calls.jsonl"

PATH_TEMPLATES = [  # most specific first; turns real URLs into the spec's path templates
    (r"^/api/v1/user/\d+/order/$", "/api/v1/user/{user_id}/order/"),
    (r"^/api/v1/reservation/\d+/issue/$", "/api/v1/reservation/{id}/issue/"),
    (r"^/api/v1/reservation/\d+/cancel/$", "/api/v1/reservation/{id}/cancel/"),
    (r"^/api/v1/order/\d+/$", "/api/v1/order/{id}/"),
    (r"^/api/v1/book/\d+/$", "/api/v1/book/{id}/"),
]


def template_of(path):
    for pattern, tpl in PATH_TEMPLATES:
        if re.match(pattern, path):
            return tpl
    return path


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def future(days=14):
    return iso(datetime.now(timezone.utc) + timedelta(days=days))


def past(days=3):
    return iso(datetime.now(timezone.utc) - timedelta(days=days))


class Api:
    """One signed-in (or anonymous) session."""

    def __init__(self, role=None):
        self.s = requests.Session()
        self.role = role or "anonymous"
        if role:
            self.login(*ACCOUNTS[role])

    def login(self, email, password):
        self.s.get(f"{BASE}/authentication/login/")
        token = self.s.cookies.get("csrftoken")
        r = self.s.post(f"{BASE}/authentication/login/",
                        data={"email": email, "password": password, "csrfmiddlewaretoken": token},
                        headers={"Referer": f"{BASE}/authentication/login/"}, allow_redirects=False)
        assert r.status_code == 302, f"Login failed for {email} (status {r.status_code}). Is the app running and seeded?"

    def call(self, method, path, json_body=None):
        headers = {"Referer": BASE + "/"}
        token = self.s.cookies.get("csrftoken")
        if token:
            headers["X-CSRFToken"] = token
        r = self.s.request(method, BASE + path, json=json_body, headers=headers)
        CALL_LOG.parent.mkdir(exist_ok=True)
        with open(CALL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"role": self.role, "method": method, "path": template_of(path),
                                "status": r.status_code,
                                "body_fields": sorted(json_body.keys()) if isinstance(json_body, dict) else []}) + "\n")
        return r

    def get(self, p): return self.call("GET", p)
    def post(self, p, b=None): return self.call("POST", p, b if b is not None else {})
    def patch(self, p, b): return self.call("PATCH", p, b)
    def delete(self, p): return self.call("DELETE", p)


def body(r):
    try:
        return r.json()
    except ValueError:
        return {}


class World:
    """Builds fresh test data (unique books) and cleans up loans/reservations afterwards."""

    def __init__(self, lib, reader, alice, bob):
        self.lib, self.reader, self.alice, self.bob = lib, reader, alice, bob
        self.users = {}
        for u in body(lib.get("/api/v1/user/")) or []:
            self.users[u["email"]] = u["id"]
        self.open_loans, self.open_reservations, self.books = [], [], []

    def uid(self, role):
        return self.users[ACCOUNTS[role][0]]

    def book(self, count=5):
        name = f"QA-{uuid.uuid4().hex[:8]}"
        r = self.lib.post("/api/v1/book/", {"name": name, "description": "api test book", "count": count})
        assert r.status_code == 201, f"Could not create a test book: {r.status_code} {r.text[:200]}"
        self.books.append(body(r)["id"])
        return body(r)["id"]

    def available(self, book_id):
        return body(self.lib.get(f"/api/v1/book/{book_id}/"))["available_count"]

    def lend(self, role, book_id, due=None):
        r = self.lib.post("/api/v1/order/", {"user": self.uid(role), "book": book_id, "plated_end_at": due or future()})
        if r.status_code == 201:
            self.open_loans.append(body(r)["id"])
        return r

    def close(self, loan_id):
        return self.lib.patch(f"/api/v1/order/{loan_id}/", {"end_at": iso(datetime.now(timezone.utc))})

    def reserve(self, client, book_id):
        r = client.post("/api/v1/reservation/", {"book": book_id})
        if r.status_code == 201:
            self.open_reservations.append((client, body(r)["id"]))
        return r

    def loans_for_book(self, book_id):
        return [o for o in body(self.lib.get("/api/v1/order/")) if o["book"] == book_id]

    def cleanup(self):
        for b in self.books:  # also closes loans started through the browser
            for o in self.loans_for_book(b):
                if o["end_at"] is None:
                    self.open_loans.append(o["id"])
        for loan_id in self.open_loans:
            self.close(loan_id)
        for client, rid in self.open_reservations:
            client.post(f"/api/v1/reservation/{rid}/cancel/", {})


@pytest.fixture(scope="session")
def clients():
    return {"lib": Api("librarian"), "reader": Api("reader"), "alice": Api("alice"), "bob": Api("bob"), "anon": Api()}


@pytest.fixture()
def world(clients):
    w = World(clients["lib"], clients["reader"], clients["alice"], clients["bob"])
    yield w
    w.cleanup()


@pytest.fixture(scope="session", autouse=True)
def fresh_call_log():
    if CALL_LOG.exists():
        CALL_LOG.unlink()
    yield
