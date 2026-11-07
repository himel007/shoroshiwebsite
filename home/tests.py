from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from home.models import HomePage, JournalPage, ProductPage


class WagtailSetupSmokeTests(TestCase):
    def test_wagtail_admin_login_page_is_available(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_homepage_editor_exposes_hero_slide_content(self):
        user = get_user_model().objects.create_superuser(
            username="hero-editor",
            email="hero-editor@example.com",
            password="test-password",
        )
        self.client.force_login(user)
        homepage = HomePage.objects.get(depth=2)

        response = self.client.get(f"/admin/pages/{homepage.id}/edit/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hero slide")
        self.assertContains(response, "Elegance That Lives Beyond Time.")
        self.assertContains(response, "SHOROSHI | ষোড়শী")

    def test_homepage_renders_shoroshi_brand_and_collection_section(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        response_html = response.content.decode("utf-8")
        self.assertEqual(response_html.count("single-hero-slider-7"), 2)
        self.assertEqual(response_html.count('class="shoroshi-service-item"'), 3)
        self.assertEqual(response_html.count('class="shoroshi-circle-category"'), 4)
        template_sections = [
            '<section class="hero-area hero-slider-7 shoroshi-hero-slider"',
            '<section class="shoroshi-service-strip"',
            '<section class="shoroshi-circle-categories"',
            '<section class="shoroshi-featured-collections"',
            'id="best-selling"',
            'id="journal"',
            'class="footer-area-wrapper shoroshi-home-footer"',
        ]
        section_positions = [response_html.index(section) for section in template_sections]
        self.assertEqual(section_positions, sorted(section_positions))
        self.assertContains(response, "single-hero-slider-7")
        self.assertContains(response, "featuted-product-wrap")
        self.assertContains(response, 'aria-label="Main navigation"')
        self.assertContains(response, 'id="shoroshi-mobile-menu"')
        self.assertContains(response, 'aria-label="Account"')
        self.assertContains(response, 'aria-label="Wishlist"')
        self.assertContains(response, 'aria-label="Shopping bag"')
        self.assertContains(response, 'href="/cart/"')
        self.assertContains(response, '<span>Collections</span>')
        self.assertContains(response, 'href="/shop/"')
        self.assertNotContains(response, '<span>Pages</span>')
        self.assertNotContains(response, '<span>Blog</span>')
        self.assertContains(response, "Shoroshi Collections")
        self.assertContains(response, "Product Information")
        self.assertContains(response, "Shop by category")
        self.assertContains(response, "SHOROSHI")
        self.assertContains(response, "ষোড়শী")
        self.assertContains(response, "Muslin Silk")
        self.assertContains(response, "Balaka Silk")
        self.assertContains(response, "Endi Silk")
        self.assertContains(response, "Joyosree Silk")
        self.assertContains(response, "SHOP NOW")
        self.assertContains(response, "Traditional sarees, chosen for your next occasion.")
        self.assertContains(response, "Shoroshi stories will appear here.")
        self.assertContains(response, 'href="#best-selling"')
        self.assertContains(response, 'href="#collections"')
        self.assertNotContains(response, 'href="#products"')
        self.assertContains(response, "No products have been added yet")
        self.assertContains(response, "images/featured/shoroshi-outfit-01.jpeg")
        self.assertContains(response, "images/featured/shoroshi-outfit-02.jpeg")
        self.assertNotContains(response, "About Us")
        self.assertNotContains(response, "New Arrivals")
        self.assertNotContains(response, "A Story Woven with Elegance")
        self.assertNotContains(response, "The Shoroshi Difference")
        self.assertNotContains(response, "Furniture")

    def test_shop_categories_page_renders_without_products(self):
        response = self.client.get("/shop/", {"cols": "3"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content.decode("utf-8").count(
                'class="hero-product-image shoroshi-shop-category'
            ),
            5,
        )
        self.assertEqual(response.context["columns"], "3")
        self.assertEqual(response.context["view_columns"], ("3", "4", "5"))
        self.assertContains(response, 'aria-label="Show 3 columns"')
        self.assertContains(response, 'aria-label="Show 5 columns"')
        self.assertContains(response, "All Collections")
        self.assertContains(response, "Filter by collection")
        self.assertContains(response, "Explore Shoroshi Collections")
        self.assertContains(response, "Muslin Silk")
        self.assertContains(response, "Balaka Silk")
        self.assertContains(response, "Endi Silk")
        self.assertContains(response, "Joyosree Silk")
        self.assertContains(response, "Browse our collections")
        self.assertNotContains(response, "No products yet")
        self.assertContains(response, "No products found in this collection yet.")

    def test_cart_page_renders_empty_state(self):
        response = self.client.get("/cart/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your bag is empty")
        self.assertContains(response, "Continue shopping")
        self.assertNotContains(response, "Proceed to checkout")

    def test_cart_add_update_and_remove_published_product(self):
        homepage = HomePage.objects.get(depth=2)
        image_buffer = BytesIO()
        PillowImage.new("RGB", (8, 8), color="red").save(image_buffer, format="PNG")
        image = get_image_model().objects.create(
            title="Cart test product",
            file=SimpleUploadedFile("cart-test.png", image_buffer.getvalue(), content_type="image/png"),
        )
        product = ProductPage(
            title="Cart Test Saree",
            slug="cart-test-saree",
            category="muslin-silk",
            sku="CART-001",
            price=Decimal("12500.00"),
            product_image=image,
            description="Verified cart test description.",
            fabric_details="Test fabric",
            colour="Wine",
            work_details="Test detailing",
            care_instructions="Test care instructions",
            is_available=True,
        )
        homepage.add_child(instance=product)
        product.save_revision().publish()

        add_response = self.client.post(
            f"/cart/add/{product.pk}/",
            {"quantity": "2"},
        )
        self.assertEqual(add_response.status_code, 302)
        cart_response = self.client.get("/cart/")
        self.assertContains(cart_response, "Cart Test Saree")
        self.assertContains(cart_response, "৳25,000.00")

        update_response = self.client.post(
            f"/cart/update/{product.pk}/",
            {"quantity": "3"},
        )
        self.assertEqual(update_response.status_code, 302)
        updated_cart = self.client.get("/cart/")
        self.assertContains(updated_cart, "৳37,500.00")

        remove_response = self.client.post(f"/cart/remove/{product.pk}/")
        self.assertEqual(remove_response.status_code, 302)
        self.assertContains(self.client.get("/cart/"), "Your bag is empty")

        product.is_available = False
        product.save_revision().publish()
        unavailable_add = self.client.post(f"/cart/add/{product.pk}/", {"quantity": "1"})
        self.assertRedirects(unavailable_add, product.url)
        self.assertNotContains(self.client.get(product.url), "Add to bag")
        self.assertContains(self.client.get("/cart/"), "Your bag is empty")

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
        self.assertContains(response, "Shoroshi Collection")
        self.assertContains(response, "product-slider-active shoroshi-home-products")
        self.assertNotContains(response, "No products have been added yet")

        detail_response = self.client.get(product.url)
        self.assertContains(detail_response, "Verified test product description.")
        self.assertContains(detail_response, 'href="/shop/"')
        self.assertNotContains(detail_response, 'href="/#products"')
        self.assertContains(detail_response, "Additional information")
        self.assertContains(detail_response, "Add to bag")
        self.assertContains(detail_response, "Fabric")
        self.assertContains(detail_response, "Care")
        self.assertNotContains(detail_response, "Add to cart")
        self.assertNotContains(detail_response, "Reviews")

        shop_response = self.client.get("/shop/", {"category": "muslin-silk"})
        self.assertEqual(shop_response.status_code, 200)
        self.assertContains(shop_response, "Test Muslin Saree")
        self.assertNotContains(shop_response, "Test Balaka Saree")

        sorted_shop_response = self.client.get("/shop/", {"sort": "price_low"})
        sorted_titles = list(
            sorted_shop_response.context["products"].values_list("title", flat=True)
        )
        self.assertEqual(sorted_titles, ["Test Muslin Saree", "Test Balaka Saree"])

        three_column_response = self.client.get("/shop/", {"cols": "3"})
        self.assertContains(
            three_column_response,
            'class="shoroshi-shop-product-grid cols-3"',
        )

        three_column_response = self.client.get("/shop/", {"cols": "3"})
        self.assertContains(
            three_column_response,
            'class="shoroshi-shop-product-grid cols-3"',
        )

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
