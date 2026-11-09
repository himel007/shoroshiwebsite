from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from home.models import Order


PASSWORD = "safe-test-pass-91"


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
        product_title="Account Test Saree",
        sku="ACC-001",
        unit_price=Decimal("5000.00"),
        quantity=1,
        line_total=Decimal("5000.00"),
    )
    return order


class AccountPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="customer",
            email="customer@example.com",
            password=PASSWORD,
            first_name="Rina",
        )
        self.other = get_user_model().objects.create_user(
            username="other", email="other@example.com", password=PASSWORD
        )

    def test_account_pages_require_login(self):
        for url in ["/account/", "/account/orders/", "/account/details/"]:
            response = self.client.get(url)
            self.assertRedirects(response, f"/account/login/?next={url}", fetch_redirect_response=False)

    def test_dashboard_without_orders(self):
        self.client.force_login(self.user)
        response = self.client.get("/account/")
        self.assertContains(response, "Hello, <strong>Rina</strong>", html=False)
        self.assertContains(response, "placed any orders yet.")
        self.assertContains(response, 'aria-current="page"')
        self.assertNotContains(response, "Delivery address")

    def test_dashboard_shows_recent_orders_and_last_address(self):
        order = make_order(self.user)
        make_order(self.other, address_line1="Someone else's street")
        self.client.force_login(self.user)
        response = self.client.get("/account/")
        self.assertContains(response, order.number)
        self.assertContains(response, "Pending confirmation")
        self.assertContains(response, "৳5,100.00")
        self.assertContains(response, "House 1, Road 2")
        self.assertNotContains(response, "Someone else")

    def test_orders_list_only_shows_own_orders(self):
        mine = make_order(self.user)
        theirs = make_order(self.other)
        self.client.force_login(self.user)
        response = self.client.get("/account/orders/")
        self.assertContains(response, mine.number)
        self.assertNotContains(response, theirs.number)

    def test_orders_list_paginates(self):
        for _ in range(12):
            make_order(self.user)
        self.client.force_login(self.user)
        response = self.client.get("/account/orders/")
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(self.client.get("/account/orders/?page=2"), "Page 2 of 2")

    def test_order_detail(self):
        order = make_order(self.user, status="shipped", notes="Please call first")
        self.client.force_login(self.user)
        response = self.client.get(f"/account/orders/{order.pk}/")
        self.assertContains(response, f"Order {order.number}")
        self.assertContains(response, "Shipped")
        self.assertContains(response, "Account Test Saree")
        self.assertContains(response, "Please call first")
        self.assertContains(response, "Cash on Delivery")

    def test_order_detail_of_another_customer_is_404(self):
        theirs = make_order(self.other)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/account/orders/{theirs.pk}/").status_code, 404)

    def test_update_account_details(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/account/details/",
            {
                "form": "details",
                "details-first_name": "Rina",
                "details-last_name": "Akter",
                "details-email": "rina@example.com",
            },
            follow=True,
        )
        self.assertContains(response, "Your account details have been saved.")
        self.user.refresh_from_db()
        self.assertEqual((self.user.last_name, self.user.email), ("Akter", "rina@example.com"))

    def test_update_rejects_email_used_by_another_account(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/account/details/",
            {
                "form": "details",
                "details-first_name": "Rina",
                "details-last_name": "",
                "details-email": "OTHER@example.com",
            },
        )
        self.assertContains(response, "Another account already uses this email.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "customer@example.com")

    def test_change_password_keeps_user_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/account/details/",
            {
                "form": "password",
                "password-old_password": PASSWORD,
                "password-new_password1": "new-Strong-pass-7781",
                "password-new_password2": "new-Strong-pass-7781",
            },
            follow=True,
        )
        self.assertContains(response, "Your password has been changed.")
        self.assertIn("_auth_user_id", self.client.session)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-Strong-pass-7781"))

    def test_change_password_rejects_wrong_old_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/account/details/",
            {
                "form": "password",
                "password-old_password": "wrong-password",
                "password-new_password1": "new-Strong-pass-7781",
                "password-new_password2": "new-Strong-pass-7781",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_header_links(self):
        self.assertContains(self.client.get("/"), 'href="/account/" aria-label="Account"')
        self.assertContains(self.client.get("/cart/"), "Log in")
        self.client.force_login(self.user)
        cart = self.client.get("/cart/")
        self.assertContains(cart, "Log out")

    def test_store_header_shows_my_account_when_logged_in(self):
        order = make_order(self.user)
        self.client.force_login(self.user)
        response = self.client.get(f"/checkout/complete/{order.pk}/")
        self.assertContains(response, 'href="/account/">My account</a>', html=False)
        self.assertContains(response, 'href="/account/orders/">View your orders</a>', html=False)
