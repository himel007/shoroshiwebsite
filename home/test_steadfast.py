from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from home import steadfast
from home.models import Order
from home.test_tracking import make_order


TEST_KEYS = dict(STEADFAST_API_KEY="key", STEADFAST_SECRET_KEY="secret")


class CodAmountTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("c", password="safe-pass-123")

    def test_full_order_cod_is_total(self):
        order = make_order(self.user)  # total 5100, amount_paid 0
        self.assertEqual(order.cod_amount_due, Decimal("5100.00"))

    def test_emi_order_cod_is_total_minus_paid(self):
        order = make_order(
            self.user, payment_plan="emi", emi_months=4,
            emi_advance=Decimal("1500.00"), emi_monthly=Decimal("875.00"),
            amount_paid=Decimal("4600.00"),
        )
        self.assertEqual(order.cod_amount_due, Decimal("500.00"))

    def test_cod_never_negative(self):
        order = make_order(self.user, amount_paid=Decimal("9999.00"))
        self.assertEqual(order.cod_amount_due, Decimal("0.00"))


@override_settings(**TEST_KEYS)
class SteadfastClientTests(TestCase):
    def test_create_order_returns_consignment(self):
        fake = mock.Mock(status_code=200)
        fake.json.return_value = {
            "status": 200,
            "message": "Consignment has been created successfully.",
            "consignment": {"consignment_id": 1424107, "tracking_code": "15BAEB8A", "status": "in_review"},
        }
        with mock.patch("home.steadfast.requests.post", return_value=fake) as post:
            consignment = steadfast.create_order(
                invoice="SH-000001", recipient_name="A", recipient_phone="01712345678",
                recipient_address="Dhaka", cod_amount=Decimal("5100.00"),
            )
        self.assertEqual(consignment["tracking_code"], "15BAEB8A")
        # Auth headers and payload are sent correctly.
        _, kwargs = post.call_args
        self.assertEqual(kwargs["headers"]["Api-Key"], "key")
        self.assertEqual(kwargs["headers"]["Secret-Key"], "secret")
        self.assertEqual(kwargs["json"]["cod_amount"], 5100.0)

    def test_create_order_raises_on_rejection(self):
        fake = mock.Mock(status_code=422)
        fake.json.return_value = {"status": 422, "message": "Invalid phone"}
        with mock.patch("home.steadfast.requests.post", return_value=fake):
            with self.assertRaises(steadfast.SteadfastError):
                steadfast.create_order(
                    invoice="SH-1", recipient_name="A", recipient_phone="x",
                    recipient_address="Dhaka", cod_amount=Decimal("10"),
                )

    def test_missing_credentials_raises(self):
        with override_settings(STEADFAST_API_KEY="", STEADFAST_SECRET_KEY=""):
            with self.assertRaises(steadfast.SteadfastError):
                steadfast.create_order(
                    invoice="SH-1", recipient_name="A", recipient_phone="01712345678",
                    recipient_address="Dhaka", cod_amount=Decimal("10"),
                )

    def test_status_label(self):
        self.assertEqual(steadfast.status_label("delivered"), "Delivered")
        self.assertEqual(steadfast.status_label(""), "Not dispatched")


@override_settings(**TEST_KEYS)
class DispatchViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_superuser("admin", "a@a.com", "safe-pass-123")
        self.customer = User.objects.create_user("cust", password="safe-pass-123")
        self.order = make_order(self.customer, status="confirmed")

    def test_dispatch_creates_consignment_and_marks_shipped(self):
        self.client.force_login(self.staff)
        fake = mock.Mock(status_code=200)
        fake.json.return_value = {
            "status": 200,
            "consignment": {"consignment_id": 999, "tracking_code": "TRK999", "status": "in_review"},
        }
        with mock.patch("home.steadfast.requests.post", return_value=fake):
            response = self.client.post(
                f"/admin/orders/{self.order.pk}/steadfast/dispatch/",
                {"cod_amount": "5100.00", "item_description": "Saree", "note": ""},
            )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.courier_consignment_id, "999")
        self.assertEqual(self.order.courier_tracking_code, "TRK999")
        self.assertEqual(self.order.courier_cod_amount, Decimal("5100.00"))
        self.assertEqual(self.order.status, "shipped")
        self.assertTrue(self.order.is_dispatched)

    def test_dispatch_requires_permission(self):
        self.client.force_login(self.customer)  # not staff
        response = self.client.get(f"/admin/orders/{self.order.pk}/steadfast/dispatch/")
        # Wagtail admin redirects non-admin users to login.
        self.assertIn(response.status_code, (302, 403))
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_dispatched)

    def test_cannot_dispatch_twice(self):
        self.order.courier_consignment_id = "111"
        self.order.save()
        self.client.force_login(self.staff)
        with mock.patch("home.steadfast.requests.post") as post:
            self.client.post(
                f"/admin/orders/{self.order.pk}/steadfast/dispatch/",
                {"cod_amount": "100", "item_description": "x", "note": ""},
            )
        post.assert_not_called()


@override_settings(**TEST_KEYS)
class TrackingLiveStatusTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("cust", password="safe-pass-123")
        self.order = make_order(
            self.user, status="shipped", courier_consignment_id="123",
            courier_tracking_code="TRK123", courier_status="in_review",
        )

    def test_track_refreshes_live_status(self):
        fake = mock.Mock(status_code=200)
        fake.json.return_value = {"status": 200, "delivery_status": "delivered"}
        with mock.patch("home.steadfast.requests.get", return_value=fake):
            response = self.client.post(
                "/track-order/",
                {"order_number": self.order.number, "phone": "01712345678"},
            )
        self.order.refresh_from_db()
        self.assertEqual(self.order.courier_status, "delivered")
        self.assertContains(response, "Delivered")
        self.assertContains(response, "TRK123")
