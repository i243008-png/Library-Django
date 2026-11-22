"""Team unit tests for the lending rules in order.services.check().

Area 1 (Hafsa). Covers:
  BR2  a copy must be available (boundary: 0 refused, 1 accepted)
  BR3  overdue = loan is open AND due date is in the past (decision table)
  BR5  the reader already holds this book on an open loan
  the order in which the rules refuse (overdue, already on loan, no copy)

The reservation branch of check() (reserving=True) is not covered here.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from authentication.models import CustomUser
from book.models import Book
from book.testing import FakeEncoderMixin
from order.models import Order
from order.services import check


def make_reader(email):
    return CustomUser.objects.create_user(
        email=email,
        password="test-password",
        first_name="Test",
        middle_name="",
        last_name="Reader",
        is_active=True,
        role=0,
    )


def code_of(refusal):
    """The refusal code, or None when check() allowed the loan."""
    return None if refusal is None else refusal.code


class CheckRuleTests(FakeEncoderMixin, TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.reader = make_reader("reader1@example.com")
        self.other = make_reader("reader2@example.com")
        self.book = Book.objects.create(name="Book A", count=2)
        self.book_b = Book.objects.create(name="Book B", count=2)

    # ---- helpers -------------------------------------------------------
    def loan(self, user, book, due, returned=False):
        return Order.objects.create(
            user=user,
            book=book,
            plated_end_at=due,
            end_at=self.now if returned else None,
        )

    def run_check(self, book=None, **kwargs):
        """check() as lend() calls it: a librarian lending, not reserving."""
        return check(
            self.reader,
            book or self.book,
            self.now,
            reserving=False,
            librarian=True,
            **kwargs,
        )

    # ---- no rule applies -----------------------------------------------
    def test_allows_the_loan_when_no_rule_applies(self):
        self.assertIsNone(self.run_check())

    # ---- BR3 decision table: C1 loan is open, C2 due date is before now --
    def test_br3_case1_open_and_past_due_refuses(self):
        self.loan(self.reader, self.book_b, self.now - timedelta(days=1))
        self.assertEqual(code_of(self.run_check()), "overdue_loan")

    def test_br3_case2_open_but_not_past_due_allows(self):
        self.loan(self.reader, self.book_b, self.now + timedelta(days=1))
        self.assertIsNone(self.run_check())

    def test_br3_case3_returned_but_past_due_allows(self):
        self.loan(self.reader, self.book_b, self.now - timedelta(days=1), returned=True)
        self.assertIsNone(self.run_check())

    def test_br3_case4_returned_and_not_past_due_allows(self):
        self.loan(self.reader, self.book_b, self.now + timedelta(days=1), returned=True)
        self.assertIsNone(self.run_check())

    # ---- BR3 boundary on the due date (strictly before now) ------------
    def test_br3_due_one_second_ago_is_overdue(self):
        self.loan(self.reader, self.book_b, self.now - timedelta(seconds=1))
        self.assertEqual(code_of(self.run_check()), "overdue_loan")

    def test_br3_due_exactly_now_is_not_overdue(self):
        self.loan(self.reader, self.book_b, self.now)
        self.assertIsNone(self.run_check())

    def test_br3_due_one_second_ahead_is_not_overdue(self):
        self.loan(self.reader, self.book_b, self.now + timedelta(seconds=1))
        self.assertIsNone(self.run_check())

    # ---- BR5 the same book already on an open loan ---------------------
    def test_br5_same_book_already_on_loan_refuses(self):
        self.loan(self.reader, self.book, self.now + timedelta(days=7))
        self.assertEqual(code_of(self.run_check()), "already_on_loan")

    def test_br5_returned_loan_of_same_book_does_not_block(self):
        self.loan(self.reader, self.book, self.now + timedelta(days=7), returned=True)
        self.assertIsNone(self.run_check())

    def test_br5_open_loan_of_another_book_does_not_block(self):
        self.loan(self.reader, self.book_b, self.now + timedelta(days=7))
        self.assertIsNone(self.run_check())

    def test_br5_own_loan_is_not_counted_as_already_on_loan(self):
        own = self.loan(self.reader, self.book, self.now + timedelta(days=7))
        self.assertIsNone(self.run_check(own_loan=own.pk))

    # ---- BR2 boundary on available copies ------------------------------
    def test_br2_zero_copies_available_refuses(self):
        single = Book.objects.create(name="Single copy", count=1)
        self.loan(self.other, single, self.now + timedelta(days=7))
        self.assertEqual(code_of(self.run_check(single)), "no_copy_available")

    def test_br2_one_copy_available_allows(self):
        single = Book.objects.create(name="Single copy", count=1)
        self.assertIsNone(self.run_check(single))

    def test_br2_copy_check_is_skipped_when_availability_is_false(self):
        single = Book.objects.create(name="Single copy", count=1)
        self.loan(self.other, single, self.now + timedelta(days=7))
        self.assertIsNone(self.run_check(single, availability=False))

    # ---- the order in which rules refuse -------------------------------
    def test_overdue_is_reported_before_already_on_loan(self):
        self.loan(self.reader, self.book, self.now - timedelta(days=1))
        self.assertEqual(code_of(self.run_check()), "overdue_loan")

    def test_already_on_loan_is_reported_before_no_copy(self):
        single = Book.objects.create(name="Single copy", count=1)
        self.loan(self.reader, single, self.now + timedelta(days=7))
        self.assertEqual(code_of(self.run_check(single)), "already_on_loan")
