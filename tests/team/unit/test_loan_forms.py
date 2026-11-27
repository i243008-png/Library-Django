"""Team unit tests for the loan forms in order/forms.py.

Area 1 (Hafsa). Covers:
  BR1  loan duration is a whole number from 1 to 30 days (default 14)
       3-point boundary values: 0, 1, 2 and 29, 30, 31
  LendForm        reader, book and days at the desk
  LoanAdminForm   a loan whose reader's account was deleted
  OrderUpdateForm the edit screen (labels, fields, widgets)
  Probes          two suspected gaps, written as "what happens today" tests

The reservation forms (CancelForm, ReservationSettingsForm) are out of scope.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from authentication.models import CustomUser
from book.models import Book
from book.testing import FakeEncoderMixin
from order.forms import IssueForm, LendForm, LoanAdminForm, OrderUpdateForm
from order.models import DELETED_READER, Order


def make_user(email, last_name="User", is_active=True):
    return CustomUser.objects.create_user(
        email=email,
        password="test-password",
        first_name="Test",
        middle_name="",
        last_name=last_name,
        is_active=is_active,
        role=0,
    )


def error_code(form, field):
    """The error code of the first error on a field."""
    return form.errors.as_data()[field][0].code


class IssueFormDaysTests(TestCase):
    """BR1: days must be a whole number from 1 to 30."""

    def days_form(self, value):
        return IssueForm(data={"days": value})

    # lower boundary: below, at, above
    def test_br1_zero_days_is_refused(self):
        form = self.days_form(0)
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "days"), "min_value")

    def test_br1_one_day_is_accepted(self):
        self.assertTrue(self.days_form(1).is_valid())

    def test_br1_two_days_is_accepted(self):
        self.assertTrue(self.days_form(2).is_valid())

    # upper boundary: below, at, above
    def test_br1_twenty_nine_days_is_accepted(self):
        self.assertTrue(self.days_form(29).is_valid())

    def test_br1_thirty_days_is_accepted(self):
        self.assertTrue(self.days_form(30).is_valid())

    def test_br1_thirty_one_days_is_refused(self):
        form = self.days_form(31)
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "days"), "max_value")

    # other classes of input
    def test_a_negative_number_of_days_is_refused(self):
        form = self.days_form(-1)
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "days"), "min_value")

    def test_a_missing_number_of_days_is_refused(self):
        form = IssueForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "days"), "required")

    def test_days_that_is_not_a_number_is_refused(self):
        form = self.days_form("abc")
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "days"), "invalid")

    def test_days_typed_as_text_is_read_as_a_whole_number(self):
        form = self.days_form("14")
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["days"], 14)

    def test_the_form_offers_14_days_and_the_limits_1_and_30(self):
        field = IssueForm().fields["days"]
        self.assertEqual(field.initial, 14)
        self.assertEqual(field.min_value, 1)
        self.assertEqual(field.max_value, 30)


class LendFormTests(FakeEncoderMixin, TestCase):
    def setUp(self):
        self.reader = make_user("reader@example.com")
        self.book = Book.objects.create(name="Book A", count=2)

    def data(self, **changes):
        values = {"reader": self.reader.pk, "book": self.book.pk, "days": 14}
        values.update(changes)
        return values

    def test_a_complete_form_is_valid(self):
        form = LendForm(data=self.data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["reader"], self.reader)
        self.assertEqual(form.cleaned_data["book"], self.book)
        self.assertEqual(form.cleaned_data["days"], 14)

    def test_an_inactive_reader_cannot_be_chosen(self):
        inactive = make_user("inactive@example.com", is_active=False)
        form = LendForm(data=self.data(reader=inactive.pk))
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "reader"), "invalid_choice")

    def test_a_missing_reader_is_refused(self):
        form = LendForm(data=self.data(reader=""))
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "reader"), "required")

    def test_an_unknown_book_is_refused(self):
        form = LendForm(data=self.data(book=999999))
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "book"), "invalid_choice")

    def test_the_day_limit_also_applies_at_the_desk(self):
        form = LendForm(data=self.data(days=31))
        self.assertFalse(form.is_valid())
        self.assertEqual(error_code(form, "days"), "max_value")

    def test_the_fields_come_in_the_order_reader_book_days(self):
        self.assertEqual(list(LendForm().fields), ["reader", "book", "days"])

    def test_readers_are_listed_by_last_name(self):
        make_user("zed@example.com", last_name="Zed")
        make_user("adams@example.com", last_name="Adams")
        listed = [u.email for u in LendForm().fields["reader"].queryset]
        # last names: Adams, User (the reader made in setUp), Zed
        self.assertEqual(
            listed, ["adams@example.com", "reader@example.com", "zed@example.com"]
        )

    def test_a_reader_is_labelled_with_name_and_email(self):
        label = LendForm().fields["reader"].label_from_instance(self.reader)
        self.assertEqual(label, "Test User (reader@example.com)")


class LoanAdminFormTests(FakeEncoderMixin, TestCase):
    def setUp(self):
        self.user = make_user("reader@example.com")
        self.book = Book.objects.create(name="Book A", count=1)
        self.due = timezone.now() + timedelta(days=7)

    def test_a_new_loan_leaves_the_reader_field_editable(self):
        field = LoanAdminForm().fields["user"]
        self.assertFalse(field.disabled)

    def test_a_loan_with_a_reader_leaves_the_reader_field_editable(self):
        loan = Order.objects.create(
            user=self.user, book=self.book, plated_end_at=self.due
        )
        field = LoanAdminForm(instance=loan).fields["user"]
        self.assertFalse(field.disabled)

    def test_a_loan_whose_reader_was_deleted_shows_the_field_disabled(self):
        orphan = Order(pk=999999, user=None, book=self.book, plated_end_at=self.due)
        field = LoanAdminForm(instance=orphan).fields["user"]
        self.assertTrue(field.disabled)
        self.assertFalse(field.required)
        self.assertEqual(field.empty_label, DELETED_READER)


class OrderUpdateFormTests(TestCase):
    def test_the_form_edits_only_the_two_dates(self):
        self.assertEqual(
            list(OrderUpdateForm().fields), ["plated_end_at", "end_at"]
        )

    def test_the_date_fields_have_readable_labels(self):
        form = OrderUpdateForm()
        self.assertEqual(
            form.fields["plated_end_at"].label, "Planned Return Date & Time"
        )
        self.assertEqual(form.fields["end_at"].label, "Actual Return Date & Time")

    def test_the_date_fields_use_a_date_time_picker(self):
        form = OrderUpdateForm()
        for name in ("plated_end_at", "end_at"):
            self.assertEqual(
                form.fields[name].widget.input_type, "datetime-local"
            )


class FormProbeTests(FakeEncoderMixin, TestCase):
    """Suspected gaps from reading the code. Each test records what the form does
    TODAY. If one fails, the form rejects the value, which is the safer behaviour:
    tell me and we turn it into a normal rule test."""

    def setUp(self):
        self.user = make_user("reader@example.com")
        self.book = Book.objects.create(name="Book A", count=1)
        self.now = timezone.now()
        self.loan = Order.objects.create(
            user=self.user, book=self.book, plated_end_at=self.now + timedelta(days=7)
        )

    @staticmethod
    def picker(moment):
        """A date and time as the browser's datetime-local box sends it."""
        return moment.strftime("%Y-%m-%dT%H:%M")

    def test_probe_a_planned_return_date_in_the_past_is_accepted(self):
        form = OrderUpdateForm(
            data={
                "plated_end_at": self.picker(self.now - timedelta(days=30)),
                "end_at": "",
            },
            instance=self.loan,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_probe_a_return_time_before_the_loan_was_created_is_accepted(self):
        form = OrderUpdateForm(
            data={
                "plated_end_at": self.picker(self.now + timedelta(days=7)),
                "end_at": self.picker(self.loan.created_at - timedelta(days=1)),
            },
            instance=self.loan,
        )
        self.assertTrue(form.is_valid(), form.errors)
