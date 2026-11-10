from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from home.models import HomePage, ProductCategory, ProductPage


class ProductCategoryTests(TestCase):
    def setUp(self):
        self.homepage = HomePage.objects.get(depth=2)
        buf = BytesIO()
        PillowImage.new("RGB", (8, 8), color="red").save(buf, format="PNG")
        self.image = get_image_model().objects.create(
            title="cat test",
            file=__import__("django.core.files.uploadedfile", fromlist=["SimpleUploadedFile"]).SimpleUploadedFile(
                "cat.png", buf.getvalue(), content_type="image/png"
            ),
        )

    def _product(self, title, sku, category):
        p = ProductPage(
            title=title, slug=sku.lower(), category=category, sku=sku,
            price=Decimal("1000.00"), product_image=self.image,
            description="d", fabric_details="f", colour="c",
            work_details="w", care_instructions="care", is_available=True,
            stock=10,
        )
        self.homepage.add_child(instance=p)
        p.save_revision().publish()
        return p

    def test_default_categories_seeded(self):
        self.assertEqual(ProductCategory.objects.count(), 4)
        self.assertTrue(ProductCategory.objects.filter(slug="muslin-silk").exists())

    def test_slug_auto_fills_from_name(self):
        c = ProductCategory.objects.create(name="Jamdani Collection")
        self.assertEqual(c.slug, "jamdani-collection")

    def test_slug_auto_fill_is_unique(self):
        # Two different names that slugify to the same base get distinct slugs.
        a = ProductCategory.objects.create(name="Silk")
        b = ProductCategory.objects.create(name="Silk!")
        self.assertEqual(a.slug, "silk")
        self.assertNotEqual(a.slug, b.slug)
        self.assertTrue(b.slug.startswith("silk"))

    def test_new_category_appears_in_shop_and_filters(self):
        jamdani = ProductCategory.objects.create(name="Jamdani", sort_order=10)
        self._product("Jamdani Saree", "JAM-1", jamdani)
        self._product("Muslin Saree", "MUS-1", ProductCategory.objects.get(slug="muslin-silk"))

        response = self.client.get("/shop/")
        self.assertContains(response, "Jamdani")

        filtered = self.client.get("/shop/?category=jamdani")
        self.assertContains(filtered, "Jamdani Saree")
        self.assertNotContains(filtered, "Muslin Saree")

    def test_product_shows_category_name(self):
        jamdani = ProductCategory.objects.create(name="Jamdani")
        product = self._product("Jamdani Saree", "JAM-2", jamdani)
        response = self.client.get(product.url)
        self.assertContains(response, "Jamdani")

    def test_category_in_use_cannot_be_deleted(self):
        from django.db.models import ProtectedError

        jamdani = ProductCategory.objects.create(name="Jamdani")
        self._product("Jamdani Saree", "JAM-3", jamdani)
        with self.assertRaises(ProtectedError):
            jamdani.delete()

    def test_admin_can_manage_categories(self):
        admin = get_user_model().objects.create_superuser(
            username="staff", email="s@example.com", password="test-password"
        )
        self.client.force_login(admin)
        listing = self.client.get("/admin/snippets/home/productcategory/")
        self.assertContains(listing, "Muslin Silk")
        add = self.client.get("/admin/snippets/home/productcategory/add/")
        self.assertEqual(add.status_code, 200)
        created = self.client.post(
            "/admin/snippets/home/productcategory/add/",
            {"name": "Cotton", "slug": "", "description": "", "sort_order": "5"},
        )
        self.assertEqual(created.status_code, 302)
        self.assertTrue(ProductCategory.objects.filter(name="Cotton").exists())
