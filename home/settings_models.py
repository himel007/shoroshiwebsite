from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting


@register_setting
class SiteContactSettings(BaseSiteSetting):
    """Site-wide contact and social links shown in the footer.

    Left blank by default: a footer link only appears once its value is set,
    so no business contact is invented.
    """

    id = models.AutoField(primary_key=True)
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="WhatsApp number in international form, e.g. 8801XXXXXXXXX (no + or spaces).",
    )
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True, help_text="Shown as 'Send us mail'.")

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("whatsapp_number"),
                FieldPanel("facebook_url"),
                FieldPanel("instagram_url"),
                FieldPanel("contact_email"),
            ],
            heading="Contact & social links",
        ),
    ]

    class Meta:
        verbose_name = "Contact & social links"
