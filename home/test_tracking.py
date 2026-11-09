from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from home.models import Order


def make_order(user, **overrides):
    data = {
        "user": user,
        "full_name": "Test Customer",
        "phone": "01712345678",
        "address_line1": "House 1, Road 2",
        "city": "Test Area",
        "district": "Test District",
        "delivery_zone_name": "Test Zone A",
        "delivery_charge": Decimal("100.00"),
        "subtotal": Decimal("5000.00"),
        "total": Decimal("5100.00"),
    }
    data.update(overrides)
    order = Order.objects.create(**data)
    order.items.create(
        product_title="Tracked Saree",
        sku="TRK-001",
        unit_price=Decimal("5000.00"),
        quantity=1,
        line_total=Decimal("5000.00"),
    )
    return order


class OrderTrackingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="customer", password="safe-test-pass-91"
        )
        self.order = make_order(self.user, status="shipped")

    def test_tracking_page_loads_without_login(self):
        response = self.client.get("/track-order/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Track your order")

    def test_track_with_number_and_phone(self):
        response = self.client.post(
            "/track-order/",
            {"order_number": self.order.number, "phone": "01712-345678"},
        )
        self.assertContains(response, f"Order {self.order.number}")
        self.assertContains(response, "Shipped")
        self.assertContains(response, "Tracked Saree")
        # Progress steps up to Shipped are marked done.
        self.assertContains(response, "is-done")

    def test_track_accepts_bare_digits(self):
        response = self.client.post(
            "/track-order/",
            {"order_number": str(self.order.pk), "phone": "01712345678"},
        )
        self.assertContains(response, f"Order {self.order.number}")

    def test_wrong_phone_is_not_found(self):
        response = self.client.post(
            "/track-order/",
            {"order_number": self.order.number, "phone": "01811111111"},
        )
        self.assertContains(response, "couldn't find an order")
        self.assertNotContains(response, "Tracked Saree")

    def test_unknown_order_number_is_not_found(self):
        response = self.client.post(
            "/track-order/",
            {"order_number": "SH-999999", "phone": "01712345678"},
        )
        self.assertContains(response, "couldn't find an order")

    def test_invalid_phone_shows_field_error(self):
        response = self.client.post(
            "/track-order/",
            {"order_number": self.order.number, "phone": "123"},
        )
        self.assertContains(response, "Bangladeshi mobile number")
        self.assertNotContains(response, "couldn't find an order")

    def test_missing_order_number_shows_field_error(self):
        response = self.client.post(
            "/track-order/",
            {"order_number": "", "phone": "01712345678"},
        )
        self.assertContains(response, "This field is required.")
        self.assertNotContains(response, "couldn't find an order")

    def test_cancelled_order_shows_cancelled_message(self):
        cancelled = make_order(self.user, status="cancelled")
        response = self.client.post(
            "/track-order/",
            {"order_number": cancelled.number, "phone": "01712345678"},
        )
        self.assertContains(response, "has been cancelled")

    def test_cannot_see_another_persons_order_without_their_phone(self):
        other = get_user_model().objects.create_user(username="other", password="x-pass-99281")
        theirs = make_order(other, phone="01999999999", full_name="Someone Else")
        response = self.client.post(
            "/track-order/",
            {"order_number": theirs.number, "phone": "01712345678"},
        )
        self.assertContains(response, "couldn't find an order")
        self.assertNotContains(response, "Someone Else")

    def test_footer_and_confirmation_link_to_tracking(self):
        self.assertContains(self.client.get("/track-order/"), 'href="/track-order/"')
        self.client.force_login(self.user)
        confirmation = self.client.get(f"/checkout/complete/{self.order.pk}/")
        self.assertContains(confirmation, 'href="/track-order/"')
