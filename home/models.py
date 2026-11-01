from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.models import Page
from wagtail.images import get_image_model_string


class HomePage(Page):
    hero_eyebrow = models.CharField(
        max_length=80,
        default="CELEBRATING THE BEAUTY OF TRADITION",
    )
    hero_description = models.TextField(
        blank=True,
        default=(
            "Discover the beauty of traditional Bengali fashion with Shoroshi. "
            "Explore our thoughtfully curated collection of luxurious sarees, "
            "elegant three-piece outfits, and timeless accessories."
        ),
    )
    hero_cta_text = models.CharField(max_length=40, default="SHOP NOW")
    hero_cta_url = models.CharField(max_length=200, default="#new-arrivals", blank=True)
    hero_secondary_cta_text = models.CharField(
        max_length=40,
        default="EXPLORE COLLECTION",
        blank=True,
    )
    hero_secondary_cta_url = models.CharField(
        max_length=200,
        default="#collections",
        blank=True,
    )
    instagram_url = models.URLField(blank=True)
    hero_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("hero_eyebrow"),
                FieldPanel("hero_description"),
                FieldPanel("hero_cta_text"),
                FieldPanel("hero_cta_url"),
                FieldPanel("hero_secondary_cta_text"),
                FieldPanel("hero_secondary_cta_url"),
                FieldPanel("hero_image"),
            ],
            heading="Homepage hero",
        ),
        MultiFieldPanel(
            [FieldPanel("instagram_url")],
            heading="Social links",
        ),
    ]
