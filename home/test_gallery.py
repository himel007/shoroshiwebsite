from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from home.models import ProductCategory, HomePage, ProductGalleryImage, ProductPage


def _image(title):
    buffer = BytesIO()
    PillowImage.new("RGB", (8, 8), color="green").save(buffer, format="PNG")
    return get_image_model().objects.create(
        title=title,
        file=SimpleUploadedFile(f"{title}.png", buffer.getvalue(), content_type="image/png"),
    )


class GalleryTests(TestCase):
    def setUp(self):
        self.homepage = HomePage.objects.get(depth=2)
        self.product = ProductPage(
            title="Gallery Saree",
            slug="gallery-saree",
            category=ProductCategory.objects.get(slug="endi-silk"),
            sku="GAL-001",
            price=Decimal("5000.00"),
            product_image=_image("cover"),
            description="Gallery test description.",
            fabric_details="f",
            colour="c",
            work_details="w",
            care_instructions="care",
            is_available=True,
            stock=5,
        )
        self.homepage.add_child(instance=self.product)
        self.product.save_revision().publish()

    def test_gallery_is_just_cover_when_no_extra_photos(self):
        self.assertEqual(len(self.product.gallery), 1)
        self.assertEqual(self.product.gallery[0]["image"], self.product.product_image)

    def test_gallery_includes_cover_then_extra_photos_in_order(self):
        ProductGalleryImage.objects.create(
            page=self.product, image=_image("extra-1"), caption="Back", sort_order=0
        )
        ProductGalleryImage.objects.create(
            page=self.product, image=_image("extra-2"), sort_order=1
        )
        gallery = self.product.gallery
        self.assertEqual(len(gallery), 3)
        # Cover is always first.
        self.assertEqual(gallery[0]["image"].title, "cover")
        self.assertEqual(gallery[1]["caption"], "Back")
        # Missing caption falls back to the product title.
        self.assertEqual(gallery[2]["caption"], "Gallery Saree")

    def test_product_page_renders_thumbnails_only_with_extra_photos(self):
        # No thumbnails for a single-image product.
        response = self.client.get(self.product.url)
        self.assertNotContains(response, "shoroshi-gallery-thumbs")

        ProductGalleryImage.objects.create(page=self.product, image=_image("extra-3"))
        response = self.client.get(self.product.url)
        self.assertContains(response, "shoroshi-gallery-thumbs")
        self.assertContains(response, "data-gallery-target")
