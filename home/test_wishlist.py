from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from home.models import HomePage, ProductPage, WishlistItem


PASSWORD = "safe-test-pass-91"


class WishlistTests(TestCase):
    def setUp(self):
        self.homepage = HomePage.objects.get(depth=2)
        image_buffer = BytesIO()
        PillowImage.new("RGB", (8, 8), color="red").save(image_buffer, format="PNG")
        self.image = get_image_model().objects.create(
            title="Wishlist test product",
            file=SimpleUploadedFile("wishlist-test.png", image_buffer.getvalue(), content_type="image/png"),
        )
        self.product = self._make_product("Wishlist Test Saree", "WISH-001", available=True)
        self.user = get_user_model().objects.create_user(
            username="customer", email="customer@example.com", password=PASSWORD
        )

    def _make_product(self, title, sku, available):
        product = ProductPage(
            title=title,
            slug=sku.lower(),
            category="balaka-silk",
            sku=sku,
            price=Decimal("8000.00"),
            product_image=self.image,
            description="Verified wishlist test description.",
            fabric_details="Test fabric",
            colour="Gold",
            work_details="Test detailing",
            care_instructions="Test care instructions",
            is_available=available,
        )
        self.homepage.add_child(instance=product)
        product.save_revision().publish()
        return product

    def _toggle(self, product, next_url=None):
        data = {"next": next_url} if next_url else {}
        return self.client.post(f"/wishlist/toggle/{product.pk}/", data)

    def test_wishlist_page_requires_login(self):
        response = self.client.get("/wishlist/")
        self.assertRedirects(response, "/account/login/?next=/wishlist/", fetch_redirect_response=False)

    def test_guest_heart_sends_to_login_then_back_to_product(self):
        response = self._toggle(self.product, next_url=self.product.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/account/login/?next={self.product.url.replace('/', '%2F')}")
        self.assertFalse(WishlistItem.objects.exists())

    def test_toggle_saves_then_removes(self):
        self.client.force_login(self.user)
        response = self._toggle(self.product, next_url=self.product.url)
        self.assertRedirects(response, self.product.url, fetch_redirect_response=False)
        self.assertTrue(WishlistItem.objects.filter(user=self.user, product=self.product).exists())

        self._toggle(self.product, next_url=self.product.url)
        self.assertFalse(WishlistItem.objects.exists())

    def test_toggle_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/wishlist/toggle/{self.product.pk}/").status_code, 405)

    def test_toggle_ignores_external_next_url(self):
        self.client.force_login(self.user)
        response = self._toggle(self.product, next_url="https://evil.example/")
        self.assertEqual(response["Location"], "/wishlist/")

    def test_toggle_unknown_product_is_404(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post("/wishlist/toggle/999999/").status_code, 404)

    def test_wishlist_page_lists_items_with_availability(self):
        unavailable = self._make_product("Sold Out Saree", "WISH-002", available=False)
        WishlistItem.objects.create(user=self.user, product=self.product)
        WishlistItem.objects.create(user=self.user, product=unavailable)
        other = get_user_model().objects.create_user(username="other", password=PASSWORD)
        hidden = self._make_product("Other Persons Saree", "WISH-003", available=True)
        WishlistItem.objects.create(user=other, product=hidden)

        self.client.force_login(self.user)
        response = self.client.get("/wishlist/")
        self.assertContains(response, "Wishlist Test Saree")
        self.assertContains(response, "৳8,000.00")
        self.assertContains(response, "Sold Out Saree")
        self.assertContains(response, "Currently unavailable")
        self.assertNotContains(response, "Other Persons Saree")
        # Only the available item gets an "Add to bag" form.
        self.assertContains(response, f'action="/cart/add/{self.product.pk}/"')
        self.assertNotContains(response, f'action="/cart/add/{unavailable.pk}/"')

    def test_unpublished_product_is_hidden_from_wishlist(self):
        WishlistItem.objects.create(user=self.user, product=self.product)
        self.product.unpublish()
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/wishlist/"), "Your wishlist is empty")

    def test_add_to_bag_from_wishlist(self):
        WishlistItem.objects.create(user=self.user, product=self.product)
        self.client.force_login(self.user)
        self.client.post(f"/cart/add/{self.product.pk}/", {"quantity": "1"})
        self.assertContains(self.client.get("/cart/"), "Wishlist Test Saree")

    def test_empty_wishlist(self):
        self.client.force_login(self.user)
        response = self.client.get("/wishlist/")
        self.assertContains(response, "Your wishlist is empty")
        self.assertContains(response, 'href="/wishlist/" class="active"', html=False)

    def test_heart_state_on_product_shop_and_home_pages(self):
        self.client.force_login(self.user)
        for url in [self.product.url, "/shop/", "/"]:
            self.assertContains(self.client.get(url), "Save Wishlist Test Saree to wishlist")
        WishlistItem.objects.create(user=self.user, product=self.product)
        for url in [self.product.url, "/shop/", "/"]:
            response = self.client.get(url)
            self.assertContains(response, "Remove Wishlist Test Saree from wishlist")
            self.assertContains(response, 'aria-pressed="true"')

    def test_unavailable_product_page_still_offers_heart(self):
        unavailable = self._make_product("Sold Out Saree", "WISH-002", available=False)
        response = self.client.get(unavailable.url)
        self.assertNotContains(response, "Add to bag")
        self.assertContains(response, "Save Sold Out Saree to wishlist")

    def test_header_links_to_wishlist(self):
        self.assertContains(self.client.get("/"), 'href="/wishlist/" aria-label="Wishlist"', html=False)
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/cart/"), 'href="/wishlist/">Wishlist</a>', html=False)

    def test_wishlist_query_only_runs_when_hearts_are_shown(self):
        self.client.force_login(self.user)
        # The cart page shows no heart buttons, so the lazy wishlist lookup must not run.
        with CaptureQueriesContext(connection) as cart_queries:
            self.client.get("/cart/")
        self.assertFalse(any("home_wishlistitem" in q["sql"] for q in cart_queries))

        with CaptureQueriesContext(connection) as shop_queries:
            self.client.get("/shop/")
        wishlist_queries = [q for q in shop_queries if "home_wishlistitem" in q["sql"]]
        self.assertEqual(len(wishlist_queries), 1)
