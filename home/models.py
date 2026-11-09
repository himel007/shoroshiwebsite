from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.models import Orderable, Page
from wagtail.images import get_image_model_string
from wagtail.search import index


PRODUCT_CATEGORIES = [
    ("muslin-silk", "Muslin Silk"),
    ("balaka-silk", "Balaka Silk"),
    ("endi-silk", "Endi Silk"),
    ("joyosree-silk", "Joyosree Silk"),
]


class HomePage(Page):
    hero_eyebrow = models.CharField(
        max_length=80,
        default="CELEBRATING THE BEAUTY OF TRADITION",
    )
    hero_description = models.TextField(
        blank=True,
        default="Traditional sarees, chosen for your next occasion.",
    )
    hero_cta_text = models.CharField(max_length=40, default="SHOP NOW")
    hero_cta_url = models.CharField(max_length=200, default="#products", blank=True)
    hero_secondary_cta_text = models.CharField(
        max_length=40,
        default="EXPLORE COLLECTION",
        blank=True,
    )
    hero_secondary_cta_url = models.CharField(max_length=200, default="#categories", blank=True)
    instagram_url = models.URLField(blank=True)
    hero_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    subpage_types = ["home.ProductPage", "home.JournalPage"]

    content_panels = Page.content_panels + [
        InlinePanel("hero_items", label="Hero slide"),
        MultiFieldPanel(
            [FieldPanel("instagram_url")],
            heading="Social links",
        ),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        selected_category = request.GET.get("category", "")
        valid_categories = {value for value, _ in PRODUCT_CATEGORIES}
        all_products = ProductPage.objects.live().public().child_of(self)
        hero_products = all_products.order_by("-first_published_at")[:2]
        products = all_products

        if selected_category in valid_categories:
            products = products.filter(category=selected_category)
        else:
            selected_category = ""

        context["product_categories"] = [
            {
                "value": value,
                "label": label,
                "number": "{:02d}".format(index),
                "count": all_products.filter(category=value).count(),
                "product": all_products.filter(category=value).first(),
            }
            for index, (value, label) in enumerate(PRODUCT_CATEGORIES, start=1)
        ]
        context["hero_products"] = hero_products
        context["hero_slides"] = self.hero_items.all()
        context["selected_category"] = selected_category
        context["selected_category_label"] = dict(PRODUCT_CATEGORIES).get(
            selected_category,
            "Shop the collection",
        )
        context["products"] = products.order_by("-first_published_at")[:8]
        context["featured_products"] = (
            all_products.filter(is_featured=True)
            .order_by("-first_published_at")[:8]
        )
        context["journal_posts"] = (
            JournalPage.objects.live()
            .public()
            .child_of(self)
            .order_by("-first_published_at")[:3]
        )
        return context


class HomePageHeroSlide(Orderable):
    id = models.AutoField(primary_key=True)
    page = ParentalKey(
        HomePage,
        on_delete=models.CASCADE,
        related_name="hero_items",
    )
    eyebrow = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    cta_text = models.CharField(max_length=40, default="Discover collection")
    cta_url = models.CharField(max_length=200, default="#best-selling", blank=True)

    panels = [
        FieldPanel("eyebrow"),
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("image"),
        FieldPanel("cta_text"),
        FieldPanel("cta_url"),
    ]


class ProductPage(Page):
    parent_page_types = ["home.HomePage"]
    subpage_types = []
    template = "home/product_page.html"

    category = models.CharField(max_length=32, choices=PRODUCT_CATEGORIES)
    sku = models.CharField(max_length=40, unique=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    product_image = models.ForeignKey(
        get_image_model_string(),
        on_delete=models.PROTECT,
        related_name="+",
    )
    description = models.TextField(max_length=600)
    fabric_details = models.CharField(max_length=120)
    colour = models.CharField(max_length=60)
    work_details = models.CharField(max_length=160)
    measurements = models.CharField(max_length=120, blank=True)
    care_instructions = models.TextField(max_length=300)
    is_available = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    search_fields = Page.search_fields + [
        index.SearchField("description"),
        index.SearchField("sku"),
        index.FilterField("category"),
        index.FilterField("is_featured"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("category"),
                FieldPanel("sku"),
                FieldPanel("price"),
                FieldPanel("product_image"),
                FieldPanel("description"),
                FieldPanel("fabric_details"),
                FieldPanel("colour"),
                FieldPanel("work_details"),
                FieldPanel("measurements"),
                FieldPanel("care_instructions"),
                FieldPanel("is_available"),
                FieldPanel("is_featured"),
            ],
            heading="Product information",
        ),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        parent_page = self.get_parent()
        if parent_page:
            context["related_products"] = (
                ProductPage.objects.live()
                .public()
                .child_of(parent_page)
                .filter(category=self.category)
                .exclude(pk=self.pk)
                .order_by("-first_published_at")[:4]
            )
        else:
            context["related_products"] = ProductPage.objects.none()
        return context


class JournalPage(Page):
    parent_page_types = ["home.HomePage"]
    subpage_types = []
    template = "home/journal_page.html"

    excerpt = models.CharField(max_length=280)
    body = models.TextField(blank=True)
    cover_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    search_fields = Page.search_fields + [index.SearchField("excerpt"), index.SearchField("body")]

    content_panels = Page.content_panels + [
        FieldPanel("excerpt"),
        FieldPanel("cover_image"),
        FieldPanel("body"),
    ]


class DeliveryZone(models.Model):
    """A delivery area with a charge set by Shoroshi staff in Wagtail admin."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=80, unique=True)
    charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Delivery charge in BDT for orders shipped to this zone.",
    )
    description = models.CharField(
        max_length=160,
        blank=True,
        help_text="Optional note shown to customers, e.g. estimated delivery time.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active zones are offered at checkout.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    panels = [
        FieldPanel("name"),
        FieldPanel("charge"),
        FieldPanel("description"),
        FieldPanel("is_active"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    PAYMENT_COD = "cod"
    PAYMENT_METHODS = [(PAYMENT_COD, "Cash on Delivery")]

    STATUS_PENDING = "pending"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending confirmation"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shoroshi_orders",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address_line1 = models.CharField("Street address", max_length=200)
    address_line2 = models.CharField("Apartment, floor, etc.", max_length=200, blank=True)
    city = models.CharField("Area / City", max_length=100)
    district = models.CharField(max_length=100)
    postcode = models.CharField(max_length=12, blank=True)
    notes = models.TextField("Order notes", max_length=500, blank=True)
    delivery_zone = models.ForeignKey(
        DeliveryZone,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    delivery_zone_name = models.CharField(max_length=80)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default=PAYMENT_COD,
    )
    staff_note = models.TextField(blank=True, help_text="Internal note, not shown to the customer.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("status"),
        FieldPanel("staff_note"),
        MultiFieldPanel(
            [
                FieldPanel("full_name", read_only=True),
                FieldPanel("phone", read_only=True),
                FieldPanel("email", read_only=True),
                FieldPanel("address_line1", read_only=True),
                FieldPanel("address_line2", read_only=True),
                FieldPanel("city", read_only=True),
                FieldPanel("district", read_only=True),
                FieldPanel("postcode", read_only=True),
                FieldPanel("notes", read_only=True),
            ],
            heading="Customer and delivery address",
        ),
        MultiFieldPanel(
            [
                FieldPanel("delivery_zone_name", read_only=True),
                FieldPanel("delivery_charge", read_only=True),
                FieldPanel("subtotal", read_only=True),
                FieldPanel("total", read_only=True),
                FieldPanel("payment_method", read_only=True),
            ],
            heading="Totals",
        ),
    ]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.number}"

    @property
    def number(self):
        return f"SH-{self.pk:06d}" if self.pk else "SH-new"


class OrderItem(models.Model):
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        ProductPage,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    product_title = models.CharField(max_length=255)
    sku = models.CharField(max_length=40)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_title} ({self.sku}) × {self.quantity} = ৳{self.line_total}"


class WishlistItem(models.Model):
    """A product a logged-in customer has saved to their wishlist."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shoroshi_wishlist",
    )
    product = models.ForeignKey(ProductPage, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_wishlist_product"),
        ]

    def __str__(self):
        return f"{self.user} ♥ {self.product}"
