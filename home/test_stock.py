from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from home.models import ProductCategory, DeliveryZone, HomePage, Order, ProductPage


PASSWORD = "safe-test-pass-91"


class StockTests(TestCase):
    def setUp(self):
        self.homepage = HomePage.objects.get(depth=2)
        buffer = BytesIO()
        PillowImage.new("RGB", (8, 8), color="blue").save(buffer, format="PNG")
        self.image = get_image_model().objects.create(
            title="Stock test product",
            file=SimpleUploadedFile("stock-test.png", buffer.getvalue(), content_type="image/png"),
        )
        self.zone = DeliveryZone.objects.create(name="Zone S", charge=Decimal("60.00"))
        self.user = get_user_model().objects.create_user(
            username="buyer", email="buyer@example.com", password=PASSWORD
        )

    def _make_product(self, sku, *, stock, is_available=True):
        product = ProductPage(
            title=f"Product {sku}",
            slug=sku.lower(),
            category=ProductCategory.objects.get(slug="endi-silk"),
            sku=sku,
            price=Decimal("1000.00"),
            product_image=self.image,
            description="Stock test description.",
            fabric_details="f",
            colour="c",
            work_details="w",
            care_instructions="care",
            is_available=is_available,
            stock=stock,
        )
        self.homepage.add_child(instance=product)
        product.save_revision().publish()
        return product

    def _address(self, zone):
        return {
            "full_name": "Buyer",
            "phone": "01712-345678",
            "email": "buyer@example.com",
            "address_line1": "House 1",
            "address_line2": "",
            "city": "Dhanmondi",
            "district": "Dhaka",
            "postcode": "",
            "delivery_zone": str(zone.pk),
            "notes": "",
        }

    # --- model helpers -------------------------------------------------
    def test_is_purchasable_requires_stock_and_availability(self):
        self.assertTrue(self._make_product("S-1", stock=3).is_purchasable)
        self.assertFalse(self._make_product("S-2", stock=0).is_purchasable)
        self.assertFalse(
            self._make_product("S-3", stock=5, is_available=False).is_purchasable
        )

    # --- cart ----------------------------------------------------------
    def test_out_of_stock_cannot_be_added(self):
        product = self._make_product("S-OOS", stock=0)
        self.client.post(f"/cart/add/{product.pk}/", {"quantity": "1"})
        self.assertEqual(self.client.session.get("shoroshi_cart", {}), {})

    def test_add_to_bag_is_capped_at_stock(self):
        product = self._make_product("S-CAP", stock=2)
        self.client.post(f"/cart/add/{product.pk}/", {"quantity": "5"})
        self.assertEqual(self.client.session["shoroshi_cart"][str(product.pk)], 2)

    def test_cart_update_is_capped_at_stock(self):
        product = self._make_product("S-UPD", stock=2)
        self.client.post(f"/cart/add/{product.pk}/", {"quantity": "1"})
        self.client.post(f"/cart/update/{product.pk}/", {"quantity": "9"})
        self.assertEqual(self.client.session["shoroshi_cart"][str(product.pk)], 2)

    # --- checkout ------------------------------------------------------
    def test_checkout_decrements_stock(self):
        product = self._make_product("S-BUY", stock=5)
        self.client.force_login(self.user)
        self.client.post(f"/cart/add/{product.pk}/", {"quantity": "3"})
        self.client.post("/checkout/", self._address(self.zone))
        product.refresh_from_db()
        self.assertEqual(product.stock, 2)
        self.assertEqual(Order.objects.count(), 1)

    def test_checkout_blocked_when_item_became_unavailable(self):
        product = self._make_product("S-GONE", stock=1)
        self.client.force_login(self.user)
        self.client.post(f"/cart/add/{product.pk}/", {"quantity": "1"})
        # Sells out after it is already in the bag.
        ProductPage.objects.filter(pk=product.pk).update(stock=0)
        response = self.client.post("/checkout/", self._address(self.zone))
        # The checkout page re-renders flagging the item instead of placing
        # the order, and nothing is charged against stock.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)

    def test_stock_is_not_oversold_across_two_orders(self):
        product = self._make_product("S-LAST", stock=1)
        other = get_user_model().objects.create_user(
            username="buyer2", email="buyer2@example.com", password=PASSWORD
        )
        # First buyer takes the only unit.
        self.client.force_login(self.user)
        self.client.post(f"/cart/add/{product.pk}/", {"quantity": "1"})
        self.client.post("/checkout/", self._address(self.zone))
        # Second buyer tries the same product.
        c2 = self.client_class()
        c2.force_login(other)
        c2.post(f"/cart/add/{product.pk}/", {"quantity": "1"})
        c2.post("/checkout/", self._address(self.zone))
        self.assertEqual(Order.objects.count(), 1)
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
