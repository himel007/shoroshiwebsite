from django.template.loader import render_to_string
from django.test import TestCase


class ErrorPageTests(TestCase):
    def test_custom_404_is_branded_and_has_search(self):
        response = self.client.get("/this-page-does-not-exist-1234/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "This page could not be found", status_code=404)
        self.assertContains(response, 'action="/search/"', status_code=404)
        self.assertContains(response, 'name="query"', status_code=404)
        self.assertContains(response, "Back to homepage", status_code=404)
        # Uses the shared store header, so navigation is available.
        self.assertContains(response, "SHOROSHI", status_code=404)

    def test_500_template_renders_standalone(self):
        html = render_to_string("500.html")
        self.assertIn("Something went wrong", html)
        self.assertIn("Back to homepage", html)
        # Must not depend on template tags/context that are unavailable during a 500.
        self.assertNotIn("{%", html)
