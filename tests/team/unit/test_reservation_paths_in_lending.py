"""Team unit tests for the reservation code that lend() depends on.

Area 1 (Hafsa). The full reservation feature is out of scope, but lend() reaches
three pieces of it, and a wrong result there would corrupt the shared record
(available copies):

  1. check(reserving=True)          already reserved, reservation limit, no copy
  2. start_loan() with a held       the reservation becomes the loan
     reservation
  3. expire_due()                   old reservations are expired before a lend

reserve() is used only to set up the reservations these paths need.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from authentication.models import ROLE_LIBRARIAN, CustomUser
from book.models import Book
from book.testing import FakeEncoderMixin
from order.models import (
    Order,
    Reservation,
    ReservationSettings,
    ReservationState,
)
from order.services import (
    RESERVATION_LIMIT,
    ReservationRefused,
    expire_due,
    lend,
    reserve,
)


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
    return Book.objects.get(pk=book.pk).available_count


class ReservationTestCase(FakeEncoderMixin, TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.hours = ReservationSettings.current_hours()
        self.librarian = make_user("librarian@example.com", ROLE_LIBRARIAN)
        self.reader = make_user("reader1@example.com")
        self.other = make_user("reader2@example.com")
        self.book = Book.objects.create(name="Single copy", count=1)

    def reserved(self, user, book):
        return reserve(user, book, now=self.now)


class ReservePathTests(ReservationTestCase):
    """check(..., reserving=True), reached through reserve()."""

    def test_reserving_a_free_book_creates_an_active_reservation(self):
        reservation = self.reserved(self.reader, self.book)
        self.assertEqual(reservation.user, self.reader)
        self.assertEqual(reservation.book, self.book)
        self.assertEqual(reservation.state, ReservationState.ACTIVE)
        self.assertEqual(
            reservation.expires_at, self.now + timedelta(hours=self.hours)
        )

    def test_a_reservation_holds_the_copy(self):
        self.assertEqual(available(self.book), 1)
        self.reserved(self.reader, self.book)
        self.assertEqual(available(self.book), 0)

    def test_reserving_the_same_book_twice_is_refused(self):
        self.reserved(self.reader, self.book)
        with self.assertRaises(ReservationRefused) as caught:
            self.reserved(self.reader, self.book)
        self.assertEqual(caught.exception.code, "already_reserved")
        self.assertEqual(Reservation.objects.filter(user=self.reader).count(), 1)

    def test_reserving_more_books_than_the_limit_is_refused(self):
        for number in range(RESERVATION_LIMIT):
            book = Book.objects.create(name=f"Limit book {number}", count=1)
            self.reserved(self.reader, book)
        extra = Book.objects.create(name="One too many", count=1)
        with self.assertRaises(ReservationRefused) as caught:
            self.reserved(self.reader, extra)
        self.assertEqual(caught.exception.code, "reservation_limit")

    def test_reserving_a_book_with_no_free_copy_is_refused(self):
        Order.objects.create(
            user=self.other, book=self.book, plated_end_at=self.now + timedelta(days=7)
        )
        with self.assertRaises(ReservationRefused) as caught:
            self.reserved(self.reader, self.book)
        self.assertEqual(caught.exception.code, "no_copy_available")


class LendWithReservationTests(ReservationTestCase):
    """start_loan(): the reservation the reader holds becomes the loan."""

    def test_lending_to_the_reader_who_reserved_issues_the_reservation(self):
        reservation = self.reserved(self.reader, self.book)
        loan = lend(self.librarian, self.reader, self.book, days=7, now=self.now)
        reservation.refresh_from_db()
        self.assertEqual(reservation.state, ReservationState.ISSUED)
        self.assertEqual(reservation.loan, loan)

    def test_the_reserved_copy_becomes_the_lent_copy_not_a_second_one(self):
        self.reserved(self.reader, self.book)
        lend(self.librarian, self.reader, self.book, days=7, now=self.now)
        self.assertEqual(available(self.book), 0)
        self.assertEqual(
            Order.objects.filter(book=self.book, end_at__isnull=True).count(), 1
        )

    def test_another_reader_cannot_lend_the_copy_a_reservation_holds(self):
        self.reserved(self.reader, self.book)
        with self.assertRaises(ReservationRefused) as caught:
            lend(self.librarian, self.other, self.book, days=7, now=self.now)
        self.assertEqual(caught.exception.code, "no_copy_available")
        self.assertEqual(Order.objects.filter(user=self.other).count(), 0)


class ExpireDueTests(ReservationTestCase):
    """expire_due(): reservations past their deadline are expired."""

    def deadline(self, reservation):
        reservation.refresh_from_db()
        return reservation.expires_at

    def test_a_reservation_is_expired_exactly_at_its_deadline(self):
        reservation = self.reserved(self.reader, self.book)
        self.assertEqual(expire_due(self.deadline(reservation)), 1)
        reservation.refresh_from_db()
        self.assertEqual(reservation.state, ReservationState.EXPIRED)

    def test_a_reservation_is_not_expired_one_second_before_its_deadline(self):
        reservation = self.reserved(self.reader, self.book)
        before = self.deadline(reservation) - timedelta(seconds=1)
        self.assertEqual(expire_due(before), 0)
        reservation.refresh_from_db()
        self.assertEqual(reservation.state, ReservationState.ACTIVE)

    def test_without_a_reader_or_book_every_due_reservation_is_expired(self):
        second_book = Book.objects.create(name="Second", count=1)
        first = self.reserved(self.reader, self.book)
        self.reserved(self.other, second_book)
        late = self.deadline(first) + timedelta(seconds=1)
        self.assertEqual(expire_due(late), 2)

    def test_with_a_reader_only_that_readers_reservations_are_expired(self):
        second_book = Book.objects.create(name="Second", count=1)
        mine = self.reserved(self.reader, self.book)
        theirs = self.reserved(self.other, second_book)
        late = self.deadline(mine) + timedelta(seconds=1)
        self.assertEqual(expire_due(late, reader=self.reader), 1)
        theirs.refresh_from_db()
        self.assertEqual(theirs.state, ReservationState.ACTIVE)

    def test_lending_frees_a_copy_whose_reservation_has_expired(self):
        reservation = self.reserved(self.reader, self.book)
        late = self.deadline(reservation) + timedelta(seconds=1)
        loan = lend(self.librarian, self.other, self.book, days=7, now=late)
        self.assertEqual(loan.user, self.other)
        reservation.refresh_from_db()
        self.assertEqual(reservation.state, ReservationState.EXPIRED)
