from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page
from wagtail.images import get_image_model_string
from wagtail.search import index


# Default categories seeded for a new site. After launch, categories are fully
# managed by staff in Wagtail admin (Snippets -> Product categories).
PRODUCT_CATEGORIES = [
    ("muslin-silk", "Muslin Silk"),
    ("balaka-silk", "Balaka Silk"),
    ("endi-silk", "Endi Silk"),
    ("joyosree-silk", "Joyosree Silk"),
]


class ProductCategory(models.Model):
    """A product collection/category, created and edited by staff in admin."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(
        max_length=90,
        unique=True,
        blank=True,
        help_text="Used in shop links, e.g. ?category=muslin-silk. Leave blank to fill it from the name automatically.",
    )
    description = models.CharField(max_length=200, blank=True)
    image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Optional image for category tiles. If empty, a product image is used.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("image"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Product category"
        verbose_name_plural = "Product categories"

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            from django.utils.text import slugify

            base = slugify(self.name) or "category"
            slug = base
            counter = 2
            while ProductCategory.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


def build_category_context(all_products, selected_slug):
    """Return (categories list, selected_slug, selected_label) for templates.

    Keeps the same dict keys (value/label/number/count/product) the templates
    already use, so category markup did not need to change.
    """
    categories = list(ProductCategory.objects.all())
    valid_slugs = {c.slug for c in categories}
    if selected_slug not in valid_slugs:
        selected_slug = ""

    category_dicts = []
    for index, category in enumerate(categories, start=1):
        in_category = all_products.filter(category=category)
        category_dicts.append(
            {
                "value": category.slug,
                "label": category.name,
                "number": "{:02d}".format(index),
                "count": in_category.count(),
                "product": in_category.first(),
                "image": category.image,
            }
        )

    selected_label = next(
        (c.name for c in categories if c.slug == selected_slug),
        "Shop the collection",
    )
    return category_dicts, selected_slug, selected_label


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

    subpage_types = [
        "home.ProductPage",
        "home.JournalPage",
        "home.ContactPage",
        "home.FAQPage",
    ]

    content_panels = Page.content_panels + [
        InlinePanel("hero_items", label="Hero slide"),
        MultiFieldPanel(
            [FieldPanel("instagram_url")],
            heading="Social links",
        ),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        all_products = ProductPage.objects.live().public().child_of(self)
        hero_products = all_products.order_by("-first_published_at")[:2]

        category_dicts, selected_category, selected_label = build_category_context(
            all_products, request.GET.get("category", "")
        )
        products = all_products
        if selected_category:
            products = products.filter(category__slug=selected_category)

        context["product_categories"] = category_dicts
        context["hero_products"] = hero_products
        context["hero_slides"] = self.hero_items.all()
        context["selected_category"] = selected_category
        context["selected_category_label"] = selected_label
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

    category = models.ForeignKey(
        "home.ProductCategory",
        null=True,
        blank=False,
        on_delete=models.PROTECT,
        related_name="products",
    )
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

    def get_category_display(self):
        """Backwards-compatible label used by the storefront templates."""
        return self.category.name if self.category_id else ""

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        parent_page = self.get_parent()
        if parent_page and self.category_id:
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

    PLAN_FULL = "full"
    PLAN_EMI = "emi"
    PAYMENT_PLANS = [
        (PLAN_FULL, "Pay in full"),
        (PLAN_EMI, "EMI (installments)"),
    ]
    EMI_ADVANCE_RATE = Decimal("0.30")
    EMI_MONTHS_CHOICES = [(3, "3 months"), (4, "4 months")]

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
    payment_plan = models.CharField(
        max_length=10,
        choices=PAYMENT_PLANS,
        default=PLAN_FULL,
    )
    emi_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of monthly installments (EMI orders only).",
    )
    emi_advance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Advance paid at order time (EMI orders only).",
    )
    emi_monthly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount of each monthly installment (EMI orders only).",
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total already collected from the customer (advance, installments, etc.). "
        "The courier COD amount is the order total minus this.",
    )
    courier_consignment_id = models.CharField(max_length=40, blank=True)
    courier_tracking_code = models.CharField(max_length=40, blank=True)
    courier_status = models.CharField(max_length=50, blank=True)
    courier_cod_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="COD amount sent to Steadfast at dispatch.",
    )
    dispatched_at = models.DateTimeField(null=True, blank=True)
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
        MultiFieldPanel(
            [
                FieldPanel("payment_plan", read_only=True),
                FieldPanel("emi_months", read_only=True),
                FieldPanel("emi_advance", read_only=True),
                FieldPanel("emi_monthly", read_only=True),
                FieldPanel("amount_paid"),
            ],
            heading="EMI plan & payments",
        ),
        MultiFieldPanel(
            [
                FieldPanel("courier_consignment_id", read_only=True),
                FieldPanel("courier_tracking_code", read_only=True),
                FieldPanel("courier_cod_amount", read_only=True),
                FieldPanel("courier_status", read_only=True),
                FieldPanel("dispatched_at", read_only=True),
            ],
            heading="Steadfast delivery",
        ),
    ]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.number}"

    @property
    def number(self):
        return f"SH-{self.pk:06d}" if self.pk else "SH-new"

    @property
    def is_emi(self):
        return self.payment_plan == self.PLAN_EMI

    @classmethod
    def calculate_emi(cls, amount, months):
        """Return (advance, monthly) for an EMI on `amount` over `months`.

        30% advance, the remaining 70% split into equal monthly installments.
        No interest. The advance absorbs any rounding remainder.
        """
        amount = Decimal(amount)
        cents = Decimal("0.01")
        monthly = (amount * (Decimal("1") - cls.EMI_ADVANCE_RATE) / Decimal(months)).quantize(
            cents, rounding=ROUND_HALF_UP
        )
        advance = (amount - monthly * Decimal(months)).quantize(cents, rounding=ROUND_HALF_UP)
        return advance, monthly

    @property
    def emi_delivery_amount(self):
        """Amount that must be paid (90% of product subtotal) before we ship."""
        if not self.is_emi:
            return None
        return (self.subtotal * Decimal("0.90")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def cod_amount_due(self):
        """What the courier should collect on delivery: total minus amount already paid."""
        due = (self.total or Decimal("0.00")) - (self.amount_paid or Decimal("0.00"))
        return due if due > 0 else Decimal("0.00")

    @property
    def is_dispatched(self):
        return bool(self.courier_consignment_id)

    @property
    def courier_status_label(self):
        from .steadfast import status_label

        return status_label(self.courier_status)


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


class ContactPage(Page):
    parent_page_types = ["home.HomePage"]
    subpage_types = []
    template = "home/contact_page.html"
    max_count = 1

    intro = models.TextField(
        blank=True,
        default="PLACEHOLDER — add a short introduction for the contact page in Wagtail admin.",
    )
    address = models.TextField(
        blank=True,
        default="PLACEHOLDER — add your shop or office address here.",
    )
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    business_hours = models.TextField(
        blank=True,
        default="PLACEHOLDER — add your opening hours here, e.g. Sat–Thu, 10am–8pm.",
    )
    map_embed_url = models.URLField(
        blank=True,
        help_text="Optional Google Maps 'embed' URL (from Share → Embed a map → src).",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        MultiFieldPanel(
            [
                FieldPanel("address"),
                FieldPanel("phone"),
                FieldPanel("email"),
                FieldPanel("business_hours"),
            ],
            heading="Contact details",
        ),
        FieldPanel("map_embed_url"),
    ]


class FAQPage(Page):
    parent_page_types = ["home.HomePage"]
    subpage_types = []
    template = "home/faq_page.html"
    max_count = 1

    intro = models.TextField(
        blank=True,
        default="PLACEHOLDER — add a short introduction for the FAQ page in Wagtail admin.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        InlinePanel("items", label="Question"),
    ]


class FAQItem(Orderable):
    id = models.AutoField(primary_key=True)
    page = ParentalKey(FAQPage, on_delete=models.CASCADE, related_name="items")
    question = models.CharField(max_length=255)
    answer = RichTextField()

    panels = [
        FieldPanel("question"),
        FieldPanel("answer"),
    ]

    def __str__(self):
        return self.question


class PrivacyPolicyPage(Page):
    parent_page_types = ["home.HomePage"]
    subpage_types = []
    template = "home/privacy_page.html"
    max_count = 1

    intro = models.TextField(
        blank=True,
        default="PLACEHOLDER — add a short introduction for the privacy policy in Wagtail admin.",
    )
    body = RichTextField(
        blank=True,
        default=(
            "<p>PLACEHOLDER — replace this with your real privacy policy in Wagtail admin. "
            "Describe what personal data you collect, how you use it, how you store it, "
            "and how customers can contact you about their data.</p>"
        ),
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]


from .settings_models import SiteContactSettings  # noqa: E402,F401
