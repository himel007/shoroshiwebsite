from decimal import Decimal

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import HomePage, PRODUCT_CATEGORIES, ProductPage


SORT_OPTIONS = [
    ("newest", "Newest"),
    ("price_low", "Price: low to high"),
    ("price_high", "Price: high to low"),
]
VIEW_COLUMNS = ("3", "4", "5")


def _bounded_quantity(value, default=1):
    try:
        return max(1, min(99, int(value)))
    except (TypeError, ValueError):
        return default


def cart(request):
    session_cart = request.session.get("shoroshi_cart", {})
    if not isinstance(session_cart, dict):
        session_cart = {}

    product_ids = []
    for product_id in session_cart:
        try:
            product_ids.append(int(product_id))
        except (TypeError, ValueError):
            continue

    products = {
        str(product.pk): product
        for product in ProductPage.objects.live().public().filter(pk__in=product_ids)
    }
    cart_items = []
    subtotal = Decimal("0.00")
    for product_id, raw_quantity in session_cart.items():
        product = products.get(str(product_id))
        if product is None:
            continue
        try:
            quantity = max(1, min(99, int(raw_quantity)))
        except (TypeError, ValueError):
            quantity = 1
        line_total = product.price * quantity
        subtotal += line_total
        cart_items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    return TemplateResponse(
        request,
        "home/cart_page.html",
        {
            "cart_items": cart_items,
            "cart_count": sum(item["quantity"] for item in cart_items),
            "subtotal": subtotal,
        },
    )


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(
        ProductPage.objects.live().public(),
        pk=product_id,
    )
    if not product.is_available:
        return redirect(product.url)

    session_cart = request.session.get("shoroshi_cart", {})
    if not isinstance(session_cart, dict):
        session_cart = {}
    key = str(product.pk)
    try:
        current_quantity = max(0, int(session_cart.get(key, 0)))
    except (TypeError, ValueError):
        current_quantity = 0
    quantity = _bounded_quantity(request.POST.get("quantity", 1))
    session_cart[key] = min(99, current_quantity + quantity)
    request.session["shoroshi_cart"] = session_cart
    return redirect("cart")


@require_POST
def cart_update(request, product_id):
    get_object_or_404(ProductPage.objects.live().public(), pk=product_id)
    session_cart = request.session.get("shoroshi_cart", {})
    if not isinstance(session_cart, dict):
        session_cart = {}
    key = str(product_id)
    if key in session_cart:
        session_cart[key] = _bounded_quantity(request.POST.get("quantity", 1))
        request.session["shoroshi_cart"] = session_cart
    return redirect("cart")


@require_POST
def cart_remove(request, product_id):
    session_cart = request.session.get("shoroshi_cart", {})
    if isinstance(session_cart, dict):
        session_cart.pop(str(product_id), None)
        request.session["shoroshi_cart"] = session_cart
    return redirect("cart")


def _wishlist_product_ids(request):
    raw_ids = request.session.get("shoroshi_wishlist", [])
    if not isinstance(raw_ids, list):
        return []
    product_ids = []
    for raw_id in raw_ids:
        try:
            product_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if product_id > 0 and product_id not in product_ids:
            product_ids.append(product_id)
    return product_ids


def wishlist(request):
    product_ids = _wishlist_product_ids(request)
    products_by_id = {
        product.pk: product
        for product in ProductPage.objects.live().public().filter(pk__in=product_ids)
    }
    wishlist_products = [
        products_by_id[product_id]
        for product_id in product_ids
        if product_id in products_by_id
    ]
    return TemplateResponse(
        request,
        "home/wishlist_page.html",
        {"wishlist_products": wishlist_products},
    )


@require_POST
def wishlist_add(request, product_id):
    product = get_object_or_404(ProductPage.objects.live().public(), pk=product_id)
    product_ids = _wishlist_product_ids(request)
    if product.pk not in product_ids:
        product_ids.append(product.pk)
        request.session["shoroshi_wishlist"] = product_ids
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("wishlist")


@require_POST
def wishlist_remove(request, product_id):
    product_ids = _wishlist_product_ids(request)
    if product_id in product_ids:
        product_ids.remove(product_id)
        request.session["shoroshi_wishlist"] = product_ids
    return redirect("wishlist")


def shop(request):
    homepage = HomePage.objects.live().first()
    all_products = ProductPage.objects.live().public()
    if homepage:
        all_products = all_products.child_of(homepage)
    else:
        all_products = all_products.none()

    valid_categories = {value for value, _ in PRODUCT_CATEGORIES}
    selected_category = request.GET.get("category", "")
    if selected_category not in valid_categories:
        selected_category = ""

    products = all_products
    if selected_category:
        products = products.filter(category=selected_category)

    sort = request.GET.get("sort", "newest")
    if sort not in dict(SORT_OPTIONS):
        sort = "newest"
    columns = request.GET.get("cols", "4")
    if columns not in VIEW_COLUMNS:
        columns = "4"
    if sort == "price_low":
        products = products.order_by("price", "title")
    elif sort == "price_high":
        products = products.order_by("-price", "title")
    else:
        products = products.order_by("-first_published_at", "title")

    page_obj = Paginator(products, 12).get_page(request.GET.get("page"))
    categories = [
        {
            "value": value,
            "label": label,
            "number": "{:02d}".format(index),
            "count": all_products.filter(category=value).count(),
            "product": all_products.filter(category=value).first(),
        }
        for index, (value, label) in enumerate(PRODUCT_CATEGORIES, start=1)
    ]

    return TemplateResponse(
        request,
        "home/shop_page.html",
        {
            "page": homepage,
            "product_categories": categories,
            "products": page_obj.object_list,
            "page_obj": page_obj,
            "selected_category": selected_category,
            "sort": sort,
            "sort_options": SORT_OPTIONS,
            "columns": columns,
            "view_columns": VIEW_COLUMNS,
        },
    )