from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from home.models import HomePage, JournalPage, ProductPage


class WagtailSetupSmokeTests(TestCase):
    def test_wagtail_admin_login_page_is_available(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_homepage_renders_shoroshi_brand_and_collection_section(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        response_html = response.content.decode("utf-8")
        self.assertEqual(response_html.count("single-hero-slider-nine"), 2)
        template_sections = [
            '<section class="hero-area hero-slider-five"',
            '<section class="shopping-support-area',
            'id="category-section"',
            'class="product-wrapper section-space--ptb_120 shoroshi-v12-product-section new-products-section"',
            "offer-colection-area",
            'id="featured-products"',
            "our-blog-area",
            "footer-area-wrapper",
        ]
        section_positions = [response_html.index(section) for section in template_sections]
        self.assertEqual(section_positions, sorted(section_positions))
        self.assertContains(response, "single-hero-slider-nine")
        self.assertContains(response, "shoroshi-v12-collage")
        self.assertContains(response, "SHOROSHI")
        self.assertContains(response, "ষোড়শী")
        self.assertContains(response, "Muslin Silk")
        self.assertContains(response, "Balaka Silk")
        self.assertContains(response, "Endi Silk")
        self.assertContains(response, "Joyosree Silk")
        self.assertContains(response, "SHOP NOW")
        self.assertContains(response, "Traditional sarees, chosen for your next occasion.")
        self.assertContains(response, "Shoroshi stories will appear here.")
        self.assertContains(response, 'href="#new-products"')
        self.assertContains(response, 'href="#category-section"')
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

        second_product = ProductPage(
            title="Test Balaka Saree",
            slug="test-balaka-saree",
            category="balaka-silk",
            sku="TEST-002",
            price=Decimal("15000.00"),
            product_image=image,
            description="Second verified test product description.",
            fabric_details="Test fabric",
            colour="Gold",
            work_details="Test detailing",
            care_instructions="Test care instructions",
            is_available=True,
            is_featured=True,
        )
        homepage.add_child(instance=second_product)
        second_product.save_revision().publish()
        self.assertEqual(
            ProductPage.objects.live().public().child_of(homepage).count(),
            2,
        )

        response = self.client.get("/", {"category": "muslin-silk"})

        self.assertEqual(len(response.context["hero_products"]), 2)
        self.assertEqual(len(response.context["featured_products"]), 1)
        self.assertEqual(len(response.context["products"]), 1)
        self.assertContains(response, "Test Muslin Saree")
        self.assertContains(response, "৳12,500.00")
        self.assertContains(response, "<h2>New Products</h2>")
        self.assertContains(response, "image-one shoroshi-v12-feature-image")
        self.assertContains(response, "image-two shoroshi-v12-feature-image")
        self.assertNotContains(response, "No products have been added yet")

        detail_response = self.client.get(product.url)
        self.assertContains(detail_response, "Verified test product description.")

    def test_published_journal_story_appears_in_v12_blog_cards(self):
        homepage = HomePage.objects.get(depth=2)
        post = JournalPage(
            title="Textile traditions",
            slug="textile-traditions",
            excerpt="A short test article excerpt.",
            body="Test article body.",
        )
        homepage.add_child(instance=post)
        post.save_revision().publish()

        response = self.client.get("/")

        self.assertContains(response, "Textile traditions")
        self.assertContains(response, "A short test article excerpt.")
        self.assertContains(response, "Read more")
