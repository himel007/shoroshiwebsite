from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from home.models import DeliveryZone, HomePage, Order, ProductPage


PASSWORD = "safe-test-pass-91"


class CheckoutTests(TestCase):
    def setUp(self):
        homepage = HomePage.objects.get(depth=2)
        image_buffer = BytesIO()
        PillowImage.new("RGB", (8, 8), color="red").save(image_buffer, format="PNG")
        image = get_image_model().objects.create(
            title="Checkout test product",
            file=SimpleUploadedFile("checkout-test.png", image_buffer.getvalue(), content_type="image/png"),
        )
        self.product = ProductPage(
            title="Checkout Test Saree",
            slug="checkout-test-saree",
            category="endi-silk",
            sku="CHK-001",
            price=Decimal("10000.00"),
            product_image=image,
            description="Verified checkout test description.",
            fabric_details="Test fabric",
            colour="Ivory",
            work_details="Test detailing",
            care_instructions="Test care instructions",
            is_available=True,
        )
        homepage.add_child(instance=self.product)
        self.product.save_revision().publish()
        self.zone = DeliveryZone.objects.create(name="Test Zone A", charge=Decimal("100.00"))
        DeliveryZone.objects.create(name="Hidden Zone", charge=Decimal("1.00"), is_active=False)
        self.user = get_user_model().objects.create_user(
            username="customer", email="customer@example.com", password=PASSWORD
        )

    def _address(self, **overrides):
        data = {
            "full_name": "Test Customer",
            "phone": "01712-345678",
            "email": "customer@example.com",
            "address_line1": "House 1, Road 2",
            "address_line2": "",
            "city": "Test Area",
            "district": "Test District",
            "postcode": "",
            "delivery_zone": str(self.zone.pk),
            "notes": "",
        }
        data.update(overrides)
        return data

    def _add_to_bag(self, quantity=1):
        self.client.post(f"/cart/add/{self.product.pk}/", {"quantity": str(quantity)})

    def _place_order(self):
        self.client.force_login(self.user)
        self._add_to_bag()
        self.client.post("/checkout/", self._address())
        return Order.objects.get()

    def test_cart_links_to_checkout(self):
        self._add_to_bag()
        self.assertContains(self.client.get("/cart/"), 'href="/checkout/"')

    def test_checkout_requires_login_and_keeps_bag(self):
        self._add_to_bag()
        response = self.client.get("/checkout/")
        self.assertRedirects(response, "/account/login/?next=/checkout/", fetch_redirect_response=False)

        login_page = self.client.get("/account/login/?next=/checkout/")
        self.assertContains(login_page, "Your bag will be kept")
        login_response = self.client.post(
            "/account/login/",
            {"username": "customer", "password": PASSWORD, "next": "/checkout/"},
        )
        self.assertRedirects(login_response, "/checkout/", fetch_redirect_response=False)
        self.assertContains(self.client.get("/checkout/"), "Checkout Test Saree")

    def test_register_logs_in_and_returns_to_checkout(self):
        response = self.client.post(
            "/account/register/",
            {
                "username": "newcustomer",
                "email": "new@example.com",
                "password1": "a-Strong-pass-4471",
                "password2": "a-Strong-pass-4471",
                "next": "/checkout/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/checkout/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(
            "/account/register/",
            {
                "username": "other",
                "email": "CUSTOMER@example.com",
                "password1": "a-Strong-pass-4471",
                "password2": "a-Strong-pass-4471",
            },
        )
        self.assertContains(response, "An account with this email already exists.")

    def test_register_ignores_external_next_url(self):
        response = self.client.post(
            "/account/register/",
            {
                "username": "n2",
                "email": "n2@example.com",
                "password1": "a-Strong-pass-4471",
                "password2": "a-Strong-pass-4471",
                "next": "https://evil.example/",
            },
        )
        self.assertEqual(response["Location"], "/shop/")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.post("/account/logout/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_empty_bag_redirects_to_cart(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get("/checkout/"), "/cart/")

    def test_place_cash_on_delivery_order(self):
        self.client.force_login(self.user)
        self._add_to_bag(2)

        page = self.client.get("/checkout/")
        self.assertContains(page, "Test Zone A")
        self.assertNotContains(page, "Hidden Zone")
        self.assertContains(page, "Cash on Delivery")
        self.assertContains(page, "৳20,000.00")

        response = self.client.post("/checkout/", self._address())
        order = Order.objects.get()
        self.assertRedirects(response, f"/checkout/complete/{order.pk}/")
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.phone, "01712345678")
        self.assertEqual(order.subtotal, Decimal("20000.00"))
        self.assertEqual(order.delivery_charge, Decimal("100.00"))
        self.assertEqual(order.total, Decimal("20100.00"))
        self.assertEqual(order.payment_method, "cod")
        self.assertEqual(order.status, "pending")
        item = order.items.get()
        self.assertEqual((item.sku, item.quantity, item.line_total), ("CHK-001", 2, Decimal("20000.00")))

        complete = self.client.get(f"/checkout/complete/{order.pk}/")
        self.assertContains(complete, order.number)
        self.assertContains(complete, "৳20,100.00")
        self.assertContains(self.client.get("/cart/"), "Your bag is empty")

        # The previous address is prefilled on the next checkout.
        self._add_to_bag()
        self.assertContains(self.client.get("/checkout/"), 'value="House 1, Road 2"')

    def test_invalid_phone_and_missing_zone_are_rejected(self):
        self.client.force_login(self.user)
        self._add_to_bag()
        response = self.client.post("/checkout/", self._address(phone="12345", delivery_zone=""))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "valid Bangladeshi mobile number")
        self.assertContains(response, "This field is required.")
        self.assertFalse(Order.objects.exists())

    def test_inactive_zone_is_rejected(self):
        self.client.force_login(self.user)
        self._add_to_bag()
        hidden = DeliveryZone.objects.get(name="Hidden Zone")
        response = self.client.post("/checkout/", self._address(delivery_zone=str(hidden.pk)))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_unavailable_item_blocks_order(self):
        self.client.force_login(self.user)
        self._add_to_bag()
        self.product.is_available = False
        self.product.save_revision().publish()
        response = self.client.post("/checkout/", self._address())
        self.assertContains(response, "currently unavailable")
        self.assertFalse(Order.objects.exists())

    def test_no_active_zones_blocks_order(self):
        DeliveryZone.objects.update(is_active=False)
        self.client.force_login(self.user)
        self._add_to_bag()
        response = self.client.post("/checkout/", self._address())
        self.assertContains(response, "delivery areas have not been set up")
        self.assertFalse(Order.objects.exists())

    def test_customer_cannot_view_another_customers_order(self):
        order = self._place_order()
        other = get_user_model().objects.create_user(username="other", password="x-pass-55821")
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/checkout/complete/{order.pk}/").status_code, 404)

    def test_admin_can_list_and_inspect_orders_and_zones(self):
        order = self._place_order()
        admin = get_user_model().objects.create_superuser(
            username="staff", email="staff@example.com", password="test-password"
        )
        self.client.force_login(admin)
        self.assertContains(self.client.get("/admin/snippets/home/order/"), order.number)
        inspect = self.client.get(f"/admin/snippets/home/order/inspect/{order.pk}/")
        self.assertContains(inspect, "Checkout Test Saree (CHK-001)")
        self.assertEqual(self.client.get(f"/admin/snippets/home/order/edit/{order.pk}/").status_code, 200)
        self.assertContains(self.client.get("/admin/snippets/home/deliveryzone/"), "Test Zone A")
