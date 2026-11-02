from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from home.models import HomePage, ProductPage


class WagtailSetupSmokeTests(TestCase):
    def test_wagtail_admin_login_page_is_available(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_homepage_renders_shoroshi_brand_and_collection_section(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SHOROSHI")
        self.assertContains(response, "ষোড়শী")
        self.assertContains(response, "Muslin Silk")
        self.assertContains(response, "Balaka Silk")
        self.assertContains(response, "Endi Silk")
        self.assertContains(response, "Joyosree Silk")
        self.assertContains(response, "SHOP NOW")
        self.assertContains(response, "Traditional sarees, chosen for your next occasion.")
        self.assertContains(response, 'href="#products"')
        self.assertContains(response, 'href="#categories"')
        self.assertContains(response, "No products have been added yet")
        self.assertNotContains(response, "About Us")
        self.assertNotContains(response, "New Arrivals")
        self.assertNotContains(response, "A Story Woven with Elegance")
        self.assertNotContains(response, "The Shoroshi Difference")
        self.assertNotContains(response, "Furniture")

    def test_published_product_appears_with_cms_price(self):
        homepage = HomePage.objects.get(depth=2)
        image_buffer = BytesIO()
        PillowImage.new("RGB", (8, 8), color="red").save(image_buffer, format="PNG")
        image = get_image_model().objects.create(
            title="Test product",
            file=SimpleUploadedFile("test-product.png", image_buffer.getvalue(), content_type="image/png"),
        )
        product = ProductPage(
            title="Test Muslin Saree",
            slug="test-muslin-saree",
            category="muslin-silk",
            sku="TEST-001",
            price=Decimal("12500.00"),
            product_image=image,
            description="Verified test product description.",
            fabric_details="Test fabric",
            colour="Wine",
            work_details="Test detailing",
            care_instructions="Test care instructions",
            is_available=True,
        )
        homepage.add_child(instance=product)
        product.save_revision().publish()

        response = self.client.get("/", {"category": "muslin-silk"})

        self.assertContains(response, "Test Muslin Saree")
        self.assertContains(response, "৳12,500.00")
        self.assertContains(response, 'id="products-title">Muslin Silk')
        self.assertNotContains(response, "No products have been added yet")

        detail_response = self.client.get(product.url)
        self.assertContains(detail_response, "Verified test product description.")
