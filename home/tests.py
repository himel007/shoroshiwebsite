from django.test import TestCase


class WagtailSetupSmokeTests(TestCase):
    def test_wagtail_admin_login_page_is_available(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)

    def test_homepage_renders_shoroshi_brand_and_collection_section(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SHOROSHI")
        self.assertContains(response, "ষোড়শী")
        self.assertContains(response, "Where Tradition Meets Timeless Elegance.")
        self.assertContains(response, "Elegance That Lives Beyond Time.")
        self.assertContains(response, "SHOP NOW")
        self.assertContains(response, "EXPLORE COLLECTION")
        self.assertContains(response, "Silk Sarees")
        self.assertContains(response, "Hand-Stitched Sarees")
        self.assertNotContains(response, "Furniture")
        self.assertNotContains(response, "[Your business")
        self.assertNotContains(response, "Welcome to your new Wagtail site")
        self.assertNotContains(response, "Welcome to your new Wagtail site")
