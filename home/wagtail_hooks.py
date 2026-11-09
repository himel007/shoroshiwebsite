from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import DeliveryZone, Order, ProductCategory


class OrderViewSet(SnippetViewSet):
    model = Order
    icon = "list-ul"
    menu_label = "Orders"
    list_display = ["number", "full_name", "phone", "total", "status", "created_at"]
    list_filter = ["status", "delivery_zone_name"]
    search_fields = ["full_name", "phone", "email"]
    inspect_view_enabled = True
    inspect_view_fields = [
        "number",
        "status",
        "created_at",
        "full_name",
        "phone",
        "email",
        "address_line1",
        "address_line2",
        "city",
        "district",
        "postcode",
        "notes",
        "items",
        "subtotal",
        "delivery_zone_name",
        "delivery_charge",
        "total",
        "payment_method",
        "staff_note",
    ]


class DeliveryZoneViewSet(SnippetViewSet):
    model = DeliveryZone
    icon = "site"
    menu_label = "Delivery zones"
    list_display = ["name", "charge", "is_active", "sort_order"]


class ProductCategoryViewSet(SnippetViewSet):
    model = ProductCategory
    icon = "tag"
    menu_label = "Product categories"
    list_display = ["name", "slug", "sort_order"]
    search_fields = ["name"]


class ShopViewSetGroup(SnippetViewSetGroup):
    items = (OrderViewSet, ProductCategoryViewSet, DeliveryZoneViewSet)
    menu_icon = "tag"
    menu_label = "Shop"
    menu_name = "shop"


register_snippet(ShopViewSetGroup)
