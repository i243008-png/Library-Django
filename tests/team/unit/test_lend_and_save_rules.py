"""Team unit tests for lend() and for the copy rule in Order.save().

Area 1 (Hafsa).

LendTests
    lend() sets the due date, takes exactly one copy, refuses with the right
    code and leaves no new loan behind, and only a librarian may lend.

OrderSaveCopyRuleTests
    The decision in Order.save():
        consumes_copy = A and (B or C or D)
        A  the loan is open (end_at is None)
        B  the loan is new (no previous row)
        C  the previous row was returned (previous end_at is set)
        D  the book changed
    Each test below changes one condition and checks whether a copy is needed.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from authentication.models import ROLE_LIBRARIAN, CustomUser
from book.models import Book
from book.testing import FakeEncoderMixin
from order.models import BookUnavailableError, Order
from order.services import PermissionDenied, ReservationRefused, lend


def make_user(email, role=0):
    return CustomUser.objects.create_user(
        email=email,
        password="test-password",
        first_name="Test",
        middle_name="",
        last_name="User",
        is_active=True,
        role=role,
    )


def available(book):
    """Available copies of a book, read fresh from the database."""
    return Book.objects.get(pk=book.pk).available_count


class LendTests(FakeEncoderMixin, TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.librarian = make_user("librarian@example.com", ROLE_LIBRARIAN)
        self.reader = make_user("reader1@example.com")
        self.other = make_user("reader2@example.com")
        self.book = Book.objects.create(name="Book A", count=2)
        self.book_b = Book.objects.create(name="Book B", count=2)

    def test_only_a_librarian_can_lend(self):
        with self.assertRaises(PermissionDenied):
            lend(self.reader, self.reader, self.book, days=14, now=self.now)

    def test_lend_by_days_sets_the_due_date_and_leaves_the_loan_open(self):
        loan = lend(self.librarian, self.reader, self.book, days=14, now=self.now)
        self.assertEqual(loan.plated_end_at, self.now + timedelta(days=14))
        self.assertIsNone(loan.end_at)

    def test_lend_with_a_due_date_uses_that_date(self):
        due = self.now + timedelta(days=3)
        loan = lend(self.librarian, self.reader, self.book, due=due, now=self.now)
        self.assertEqual(loan.plated_end_at, due)

    def test_lend_saves_the_loan_for_the_reader_and_book(self):
        loan = lend(self.librarian, self.reader, self.book, days=7, now=self.now)
        saved = Order.objects.get(pk=loan.pk)
        self.assertEqual(saved.user, self.reader)
        self.assertEqual(saved.book, self.book)

    def test_lend_takes_exactly_one_copy_and_keeps_the_total(self):
        before = available(self.book)
        lend(self.librarian, self.reader, self.book, days=7, now=self.now)
        self.assertEqual(available(self.book), before - 1)
        self.assertEqual(Book.objects.get(pk=self.book.pk).count, 2)

    def test_lend_is_refused_when_no_copy_is_available_and_nothing_is_saved(self):
        single = Book.objects.create(name="Single copy", count=1)
        Order.objects.create(
            user=self.other, book=single, plated_end_at=self.now + timedelta(days=7)
        )
        with self.assertRaises(ReservationRefused) as caught:
            lend(self.librarian, self.reader, single, days=7, now=self.now)
        self.assertEqual(caught.exception.code, "no_copy_available")
        self.assertEqual(Order.objects.filter(user=self.reader).count(), 0)
        self.assertEqual(available(single), 0)

    def test_lend_is_refused_when_the_reader_has_an_overdue_loan(self):
        Order.objects.create(
            user=self.reader,
            book=self.book_b,
            plated_end_at=self.now - timedelta(days=1),
        )
        with self.assertRaises(ReservationRefused) as caught:
            lend(self.librarian, self.reader, self.book, days=7, now=self.now)
        self.assertEqual(caught.exception.code, "overdue_loan")
        self.assertEqual(Order.objects.filter(user=self.reader).count(), 1)

    def test_a_repeated_lend_of_the_same_book_creates_no_duplicate(self):
        lend(self.librarian, self.reader, self.book, days=7, now=self.now)
        with self.assertRaises(ReservationRefused) as caught:
            lend(self.librarian, self.reader, self.book, days=7, now=self.now)
        self.assertEqual(caught.exception.code, "already_on_loan")
        open_loans = Order.objects.filter(
            user=self.reader, book=self.book, end_at__isnull=True
        )
        self.assertEqual(open_loans.count(), 1)


class OrderSaveCopyRuleTests(FakeEncoderMixin, TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.due = self.now + timedelta(days=7)
        self.u1 = make_user("reader1@example.com")
        self.u2 = make_user("reader2@example.com")
        self.single = Book.objects.create(name="Single copy", count=1)
        self.other_book = Book.objects.create(name="Other book", count=1)

    def hold(self, user, book):
        """An open loan: it takes a copy."""
        return Order.objects.create(user=user, book=book, plated_end_at=self.due)

    def returned(self, user, book):
        """A returned loan: it takes no copy."""
        return Order.objects.create(
            user=user, book=book, plated_end_at=self.due, end_at=self.now
        )

    # A true, B true: a new open loan needs a copy
    def test_new_open_loan_takes_the_copy_when_one_is_available(self):
        self.hold(self.u1, self.single)
        self.assertEqual(available(self.single), 0)

    def test_new_open_loan_is_refused_when_no_copy_is_available(self):
        self.hold(self.u2, self.single)
        with self.assertRaises(BookUnavailableError):
            self.hold(self.u1, self.single)
        self.assertEqual(Order.objects.filter(user=self.u1).count(), 0)

    # A false, B true: a new loan saved already returned needs no copy
    def test_new_returned_loan_needs_no_copy(self):
        self.hold(self.u2, self.single)
        self.returned(self.u1, self.single)
        self.assertEqual(available(self.single), 0)

    # A true, B false, C false, D false: saving an unchanged open loan needs no copy
    def test_saving_an_unchanged_open_loan_needs_no_copy(self):
        loan = self.hold(self.u1, self.single)
        loan.plated_end_at = self.due + timedelta(days=1)
        loan.save()
        self.assertEqual(available(self.single), 0)

    # C true: reopening a returned loan needs a copy
    def test_reopening_a_returned_loan_takes_a_copy_when_one_is_available(self):
        loan = self.returned(self.u1, self.single)
        loan.end_at = None
        loan.save()
        self.assertEqual(available(self.single), 0)

    def test_reopening_a_returned_loan_is_refused_when_no_copy_is_available(self):
        loan = self.returned(self.u1, self.single)
        self.hold(self.u2, self.single)
        loan.end_at = None
        with self.assertRaises(BookUnavailableError):
            loan.save()
        self.assertIsNotNone(Order.objects.get(pk=loan.pk).end_at)

    # D true: moving an open loan to another book needs a copy of that book
    def test_moving_an_open_loan_takes_a_copy_of_the_new_book(self):
        loan = self.hold(self.u1, self.single)
        loan.book = self.other_book
        loan.save()
        self.assertEqual(available(self.other_book), 0)
        self.assertEqual(available(self.single), 1)

    def test_moving_an_open_loan_is_refused_when_the_new_book_has_no_copy(self):
        loan = self.hold(self.u1, self.single)
        self.hold(self.u2, self.other_book)
        loan.book = self.other_book
        with self.assertRaises(BookUnavailableError):
            loan.save()
        self.assertEqual(Order.objects.get(pk=loan.pk).book, self.single)
