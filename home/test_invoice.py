from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from home.models import DeliveryZone, Order, OrderItem


PASSWORD = "safe-test-pass-91"


class InvoiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="buyer", email="buyer@example.com", password=PASSWORD
        )
        self.zone = DeliveryZone.objects.create(name="Zone I", charge=Decimal("60.00"))
        self.order = Order.objects.create(
            user=self.user,
            full_name="Test Buyer",
            phone="01712-345678",
            email="buyer@example.com",
            address_line1="House 1",
            city="Dhanmondi",
            district="Dhaka",
            delivery_zone=self.zone,
            delivery_zone_name=self.zone.name,
            delivery_charge=self.zone.charge,
            subtotal=Decimal("1000.00"),
            total=Decimal("1060.00"),
        )
        OrderItem.objects.create(
            order=self.order,
            product_title="Test Saree",
            sku="INV-001",
            unit_price=Decimal("1000.00"),
            quantity=1,
            line_total=Decimal("1000.00"),
        )

    def test_owner_can_view_their_invoice(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/invoice/{self.order.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.number)
        self.assertContains(response, "Test Saree")
        self.assertContains(response, "INVOICE")

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(f"/invoice/{self.order.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/account/login/", response["Location"])

    def test_other_customer_cannot_view_invoice(self):
        other = get_user_model().objects.create_user(
            username="intruder", email="x@example.com", password=PASSWORD
        )
        self.client.force_login(other)
        response = self.client.get(f"/invoice/{self.order.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_staff_can_view_any_invoice(self):
        staff = get_user_model().objects.create_user(
            username="staff", email="s@example.com", password=PASSWORD,
            is_staff=True,
        )
        self.client.force_login(staff)
        response = self.client.get(f"/invoice/{self.order.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.number)
