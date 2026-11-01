from django.db import models

from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.models import Page
from wagtail.images import get_image_model_string


class HomePage(Page):
    hero_eyebrow = models.CharField(max_length=80, default="Shoroshi Bangladesh")
    hero_description = models.TextField(
        blank=True,
        default="Furniture for the spaces you call home.",
    )
    hero_cta_text = models.CharField(max_length=40, default="Explore collection")
    hero_cta_url = models.CharField(max_length=200, default="#collections", blank=True)
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
                FieldPanel("hero_image"),
            ],
            heading="Homepage hero",
        ),
    ]
