"""Team unit tests for the rest of the loan code in order/models.py.

Area 1 (Hafsa). Covers:
  audit helpers          as_text(), reader_label()
  bulk-write guards      OrderQuerySet.bulk_update / update / bulk_create
  text forms             __str__, __repr__, to_dict
  partial saves          Order.save(update_fields=...)
  "a loan needs a reader"
  returning a loan       end_at set -> the copy is released (Workflow 2)
  static helpers         create, get_by_id, update, get_all,
                         get_not_returned_books, delete_by_id
  start_loan() race      the last copy disappears between check and save
"""

from datetime import timedelta
from unittest.mock import patch

from django.db import DataError
from django.test import TestCase
from django.utils import timezone

from authentication.models import ROLE_LIBRARIAN, CustomUser
from book.models import Book
from book.testing import FakeEncoderMixin
from order.models import (
    DELETED_READER,
    BookUnavailableError,
    Order,
    as_text,
    reader_label,
)
from order.services import ReservationRefused, lend


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


class LoanModelTests(FakeEncoderMixin, TestCase):
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

    # ---- audit helpers -------------------------------------------------
    def test_as_text_reads_an_iso_string_and_returns_utc(self):
        self.assertEqual(
            as_text("2026-11-21T10:00:00+00:00"), "2026-11-21T10:00:00+00:00"
        )

    def test_as_text_converts_another_zone_to_utc(self):
        self.assertEqual(
            as_text("2026-11-21T10:00:00+05:00"), "2026-11-21T05:00:00+00:00"
        )

    def test_as_text_of_nothing_is_none(self):
        self.assertIsNone(as_text(None))

    def test_reader_label_names_the_reader_and_the_id(self):
        self.assertEqual(reader_label(self.u1), f"Test User #{self.u1.pk}")

    def test_reader_label_of_a_deleted_account(self):
        self.assertEqual(reader_label(None), DELETED_READER)

    # ---- bulk-write guards ---------------------------------------------
    def test_bulk_update_of_an_audited_field_is_refused(self):
        loan = self.hold(self.u1, self.single)
        with self.assertRaises(ValueError):
            Order.objects.bulk_update([loan], ["end_at"])

    def test_bulk_update_of_the_due_date_is_allowed(self):
        loan = self.hold(self.u1, self.single)
        loan.plated_end_at = self.due + timedelta(days=1)
        self.assertEqual(Order.objects.bulk_update([loan], ["plated_end_at"]), 1)

    def test_queryset_update_of_an_audited_field_is_refused(self):
        loan = self.hold(self.u1, self.single)
        with self.assertRaises(ValueError):
            Order.objects.filter(pk=loan.pk).update(end_at=self.now)

    def test_queryset_update_of_the_due_date_is_allowed(self):
        loan = self.hold(self.u1, self.single)
        changed = Order.objects.filter(pk=loan.pk).update(plated_end_at=self.due)
        self.assertEqual(changed, 1)

    def test_bulk_create_is_refused(self):
        with self.assertRaises(ValueError):
            Order.objects.bulk_create(
                [Order(user=self.u1, book=self.single, plated_end_at=self.due)]
            )

    # ---- text forms ----------------------------------------------------
    def test_str_shows_the_loan_reader_and_book(self):
        loan = self.hold(self.u1, self.single)
        self.assertEqual(
            str(loan), f"Order #{loan.id} ({self.u1.email} - {self.single.name})"
        )

    def test_str_of_a_loan_without_a_reader_says_deleted_reader(self):
        loan = self.hold(self.u1, self.single)
        loan.user = None
        self.assertIn(DELETED_READER, str(loan))

    def test_repr_shows_the_class_and_id(self):
        loan = self.hold(self.u1, self.single)
        self.assertEqual(repr(loan), f"Order(id={loan.id})")

    def test_to_dict_is_not_implemented_and_returns_none(self):
        # FINDING: the docstring promises a dict (id, book, user, dates) but the
        # body is "pass". Recorded as a low-severity defect candidate.
        loan = self.hold(self.u1, self.single)
        self.assertIsNone(loan.to_dict())

    # ---- partial saves: Order.save(update_fields=...) -------------------
    def test_save_with_no_fields_does_nothing(self):
        loan = self.hold(self.u1, self.single)
        loan.plated_end_at = self.due + timedelta(days=5)
        self.assertIsNone(loan.save(update_fields=[]))
        self.assertEqual(Order.objects.get(pk=loan.pk).plated_end_at, self.due)

    def test_partial_save_ignores_an_unsaved_book_change(self):
        self.hold(self.u2, self.other_book)  # no copy left of other_book
        loan = self.hold(self.u1, self.single)
        loan.book = self.other_book
        loan.plated_end_at = self.due + timedelta(days=1)
        loan.save(update_fields=["plated_end_at"])  # no copy check, no error
        self.assertEqual(Order.objects.get(pk=loan.pk).book, self.single)

    def test_partial_save_ignores_an_unsaved_reader_change(self):
        loan = self.hold(self.u1, self.single)
        loan.user = self.u2
        loan.plated_end_at = self.due + timedelta(days=1)
        loan.save(update_fields=["plated_end_at"])
        self.assertEqual(Order.objects.get(pk=loan.pk).user, self.u1)

    def test_partial_save_ignores_an_unsaved_reopen(self):
        loan = self.returned(self.u1, self.single)
        self.hold(self.u2, self.single)  # the copy is gone
        loan.end_at = None
        loan.save(update_fields=["plated_end_at"])  # not reopened, so no error
        self.assertIsNotNone(Order.objects.get(pk=loan.pk).end_at)

    def test_partial_save_applies_the_named_book_and_reader(self):
        loan = self.hold(self.u1, self.single)
        loan.book = self.other_book
        loan.user = self.u2
        loan.save(update_fields=["book", "user"])
        saved = Order.objects.get(pk=loan.pk)
        self.assertEqual(saved.book, self.other_book)
        self.assertEqual(saved.user, self.u2)
        self.assertEqual(available(self.other_book), 0)

    def test_partial_save_of_end_at_closes_the_loan(self):
        loan = self.hold(self.u1, self.single)
        loan.end_at = self.now
        loan.save(update_fields=["end_at"])
        self.assertEqual(available(self.single), 1)

    # ---- a loan needs a reader -----------------------------------------
    def test_a_new_loan_without_a_reader_is_refused(self):
        loan = Order(user=None, book=self.single, plated_end_at=self.due)
        with self.assertRaises(ValueError):
            loan.save()

    # ---- returning a loan (Workflow 2) ----------------------------------
    def test_closing_a_loan_releases_the_copy(self):
        loan = self.hold(self.u1, self.single)
        self.assertEqual(available(self.single), 0)
        loan.end_at = self.now
        loan.save()
        self.assertEqual(available(self.single), 1)
        self.assertIsNotNone(Order.objects.get(pk=loan.pk).end_at)

    def test_changing_the_return_time_of_a_closed_loan_changes_no_copy(self):
        loan = self.hold(self.u1, self.single)
        loan.end_at = self.now
        loan.save()
        loan.end_at = self.now + timedelta(hours=1)
        loan.save()
        self.assertEqual(available(self.single), 1)

    # ---- static helpers --------------------------------------------------
    def test_create_returns_the_saved_loan(self):
        loan = Order.create(self.u1, self.single, self.due)
        self.assertEqual(Order.objects.get(pk=loan.pk).user, self.u1)

    def test_create_returns_none_without_a_reader(self):
        self.assertIsNone(Order.create(None, self.single, self.due))

    def test_create_returns_none_when_no_copy_is_available(self):
        self.hold(self.u2, self.single)
        self.assertIsNone(Order.create(self.u1, self.single, self.due))

    def test_create_returns_none_on_a_database_data_error(self):
        with patch.object(Order, "save", side_effect=DataError("bad value")):
            self.assertIsNone(Order.create(self.u1, self.single, self.due))

    def test_get_by_id_finds_a_loan(self):
        loan = self.hold(self.u1, self.single)
        self.assertEqual(Order.get_by_id(loan.pk), loan)

    def test_get_by_id_returns_none_for_a_missing_loan(self):
        self.assertIsNone(Order.get_by_id(999999))

    def test_update_changes_the_due_date(self):
        loan = self.hold(self.u1, self.single)
        later = self.due + timedelta(days=3)
        loan.update(plated_end_at=later)
        self.assertEqual(Order.objects.get(pk=loan.pk).plated_end_at, later)

    def test_update_with_a_return_time_closes_the_loan(self):
        loan = self.hold(self.u1, self.single)
        loan.update(end_at=self.now)
        self.assertEqual(available(self.single), 1)

    def test_get_all_lists_the_loans(self):
        first = self.hold(self.u1, self.single)
        second = self.hold(self.u2, self.other_book)
        self.assertIn(first, Order.get_all())
        self.assertIn(second, Order.get_all())

    def test_get_not_returned_books_lists_only_open_loans(self):
        open_loan = self.hold(self.u1, self.single)
        closed = self.returned(self.u2, self.other_book)
        ids = [row["id"] for row in Order.get_not_returned_books()]
        self.assertIn(open_loan.pk, ids)
        self.assertNotIn(closed.pk, ids)

    def test_delete_by_id_removes_a_loan(self):
        loan = self.hold(self.u1, self.single)
        self.assertTrue(Order.delete_by_id(loan.pk))
        self.assertFalse(Order.objects.filter(pk=loan.pk).exists())

    def test_delete_by_id_returns_false_for_a_missing_loan(self):
        self.assertFalse(Order.delete_by_id(999999))


class StartLoanRaceTests(FakeEncoderMixin, TestCase):
    def test_lend_is_refused_when_the_last_copy_goes_between_check_and_save(self):
        now = timezone.now()
        librarian = make_user("librarian@example.com", ROLE_LIBRARIAN)
        reader = make_user("reader@example.com")
        book = Book.objects.create(name="Single copy", count=1)
        with patch.object(Order, "save", side_effect=BookUnavailableError("gone")):
            with self.assertRaises(ReservationRefused) as caught:
                lend(librarian, reader, book, days=7, now=now)
        self.assertEqual(caught.exception.code, "no_copy_available")
        self.assertEqual(Order.objects.filter(user=reader).count(), 0)
