from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.widgets import Button
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import IndexView, SnippetViewSet, SnippetViewSetGroup

from .models import DeliveryZone, Order, ProductCategory
from . import steadfast_admin


class OrderIndexView(IndexView):
    def get_list_more_buttons(self, instance):
        buttons = super().get_list_more_buttons(instance)
        buttons.append(
            Button(
                "Invoice",
                url=reverse("invoice", args=[instance.pk]),
                icon_name="doc-full",
                priority=60,
                attrs={"target": "_blank"},
            )
        )
        if instance.is_dispatched:
            buttons.append(
                Button(
                    "Refresh courier status",
                    url=reverse("steadfast_refresh", args=[instance.pk]),
                    icon_name="rotate",
                    priority=70,
                )
            )
        else:
            buttons.append(
                Button(
                    "Send to Steadfast",
                    url=reverse("steadfast_dispatch", args=[instance.pk]),
                    icon_name="download",
                    priority=65,
                )
            )
        return buttons


class OrderViewSet(SnippetViewSet):
    model = Order
    icon = "list-ul"
    menu_label = "Orders"
    index_view_class = OrderIndexView
    list_display = ["number", "full_name", "phone", "total", "status", "courier_status", "created_at"]
    list_filter = ["status", "payment_plan", "delivery_zone_name"]
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
        "payment_plan",
        "emi_months",
        "emi_advance",
        "emi_monthly",
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


@hooks.register("register_admin_urls")
def register_steadfast_urls():
    return [
        path(
            "orders/<int:pk>/steadfast/dispatch/",
            steadfast_admin.dispatch_to_steadfast,
            name="steadfast_dispatch",
        ),
        path(
            "orders/<int:pk>/steadfast/refresh/",
            steadfast_admin.refresh_steadfast_status,
            name="steadfast_refresh",
        ),
    ]
