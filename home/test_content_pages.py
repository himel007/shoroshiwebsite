from django.test import TestCase
from wagtail.models import Site

from home.models import ContactPage, FAQPage, SiteContactSettings


class ContentPageTests(TestCase):
    def test_contact_and_faq_pages_exist_from_migration(self):
        self.assertEqual(ContactPage.objects.count(), 1)
        self.assertEqual(FAQPage.objects.count(), 1)
        faq = FAQPage.objects.first()
        self.assertEqual(faq.items.count(), 4)

    def test_contact_page_renders(self):
        contact = ContactPage.objects.first()
        response = self.client.get(contact.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contact")
        # Placeholder copy is present until staff edit it.
        self.assertContains(response, "PLACEHOLDER")

    def test_contact_page_shows_filled_details_and_hides_blanks(self):
        contact = ContactPage.objects.first()
        contact.phone = "01712345678"
        contact.email = "hello@example.com"
        contact.map_embed_url = ""
        contact.save_revision().publish()
        response = self.client.get(contact.url)
        self.assertContains(response, 'href="tel:01712345678"')
        self.assertContains(response, 'href="mailto:hello@example.com"')
        self.assertNotContains(response, "<iframe")

    def test_faq_page_renders_questions_as_accordion(self):
        faq = FAQPage.objects.first()
        response = self.client.get(faq.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<details")
        self.assertContains(response, "How do I place an order")

    def test_footer_links_to_faq_and_contact(self):
        response = self.client.get("/cart/")
        self.assertContains(response, 'href="/faq/"')
        self.assertContains(response, 'href="/contact/"')
        self.assertContains(response, 'href="/track-order/"')

    def test_footer_social_links_appear_only_when_configured(self):
        # No settings configured: no social anchors rendered.
        response = self.client.get("/cart/")
        self.assertNotContains(response, 'href="https://wa.me/')
        self.assertNotContains(response, 'aria-label="Facebook"')

        site = Site.objects.get(is_default_site=True)
        settings = SiteContactSettings.for_site(site)
        settings.whatsapp_number = "8801712345678"
        settings.facebook_url = "https://facebook.com/shoroshi"
        settings.instagram_url = "https://instagram.com/shoroshi"
        settings.contact_email = "hello@example.com"
        settings.save()

        response = self.client.get("/cart/")
        self.assertContains(response, 'href="https://wa.me/8801712345678"')
        self.assertContains(response, 'href="https://facebook.com/shoroshi"')
        self.assertContains(response, 'href="https://instagram.com/shoroshi"')
        self.assertContains(response, 'href="mailto:hello@example.com"')
        self.assertContains(response, "Send us mail")

    def test_homepage_footer_has_help_and_social(self):
        response = self.client.get("/")
        self.assertContains(response, ">FAQ<")
        self.assertContains(response, ">Contact<")
        self.assertContains(response, "shoroshi-footer-social")

    def test_only_one_contact_and_faq_allowed(self):
        self.assertEqual(ContactPage.max_count, 1)
        self.assertEqual(FAQPage.max_count, 1)
