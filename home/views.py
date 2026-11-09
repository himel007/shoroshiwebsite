from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AccountDetailsForm, CheckoutForm, CustomerRegistrationForm
from .models import DeliveryZone, HomePage, Order, OrderItem, PRODUCT_CATEGORIES, ProductPage


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


CART_SESSION_KEY = "shoroshi_cart"


def _session_cart(request):
    session_cart = request.session.get(CART_SESSION_KEY, {})
    return session_cart if isinstance(session_cart, dict) else {}


def _cart_contents(request):
    """Return (cart_items, subtotal) priced from live product pages."""
    session_cart = _session_cart(request)
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
        quantity = _bounded_quantity(raw_quantity)
        line_total = product.price * quantity
        subtotal += line_total
        cart_items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
            }
        )
    return cart_items, subtotal


def cart(request):
    cart_items, subtotal = _cart_contents(request)
    return TemplateResponse(
        request,
        "home/cart_page.html",
        {
            "cart_items": cart_items,
            "cart_count": sum(item["quantity"] for item in cart_items),
            "subtotal": subtotal,
        },
    )


@login_required
def checkout(request):
    cart_items, subtotal = _cart_contents(request)
    if not cart_items:
        messages.info(request, "Your bag is empty. Add an item before checking out.")
        return redirect("cart")

    unavailable = [item["product"] for item in cart_items if not item["product"].is_available]
    zones = DeliveryZone.objects.filter(is_active=True)

    if request.method == "POST" and not unavailable and zones.exists():
        form = CheckoutForm(request.POST)
        if form.is_valid():
            zone = form.cleaned_data["delivery_zone"]
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.delivery_zone_name = zone.name
                order.delivery_charge = zone.charge
                order.subtotal = subtotal
                order.total = subtotal + zone.charge
                order.payment_method = Order.PAYMENT_COD
                order.save()
                OrderItem.objects.bulk_create(
                    [
                        OrderItem(
                            order=order,
                            product=item["product"],
                            product_title=item["product"].title,
                            sku=item["product"].sku,
                            unit_price=item["product"].price,
                            quantity=item["quantity"],
                            line_total=item["line_total"],
                        )
                        for item in cart_items
                    ]
                )
            request.session[CART_SESSION_KEY] = {}
            return redirect("checkout_complete", order_id=order.pk)
    else:
        form = CheckoutForm(initial=_checkout_initial(request.user))

    return TemplateResponse(
        request,
        "home/checkout_page.html",
        {
            "form": form,
            "cart_items": cart_items,
            "cart_count": sum(item["quantity"] for item in cart_items),
            "subtotal": subtotal,
            "unavailable_products": unavailable,
            "delivery_zones": zones,
        },
    )


def _checkout_initial(user):
    previous = Order.objects.filter(user=user).first()
    if previous:
        fields = ["full_name", "phone", "email", "address_line1", "address_line2",
                  "city", "district", "postcode"]
        initial = {name: getattr(previous, name) for name in fields}
        if previous.delivery_zone_id:
            initial["delivery_zone"] = previous.delivery_zone_id
        return initial
    return {"full_name": user.get_full_name(), "email": user.email}


@login_required
def checkout_complete(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return TemplateResponse(
        request,
        "home/checkout_complete.html",
        {"order": order, "order_items": order.items.all()},
    )


@login_required
def account_dashboard(request):
    orders = Order.objects.filter(user=request.user)
    return TemplateResponse(
        request,
        "home/account_dashboard.html",
        {
            "account_section": "dashboard",
            "recent_orders": orders[:5],
            "order_count": orders.count(),
            "last_order": orders.first(),
        },
    )


@login_required
def account_orders(request):
    orders = Order.objects.filter(user=request.user)
    page_obj = Paginator(orders, 10).get_page(request.GET.get("page"))
    return TemplateResponse(
        request,
        "home/account_orders.html",
        {"account_section": "orders", "orders": page_obj.object_list, "page_obj": page_obj},
    )


@login_required
def account_order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return TemplateResponse(
        request,
        "home/account_order_detail.html",
        {"account_section": "orders", "order": order, "order_items": order.items.all()},
    )


@login_required
def account_details(request):
    details_form = AccountDetailsForm(instance=request.user, prefix="details")
    password_form = PasswordChangeForm(request.user, prefix="password")
    if request.method == "POST":
        if request.POST.get("form") == "password":
            password_form = PasswordChangeForm(request.user, request.POST, prefix="password")
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed.")
                return redirect("account_details")
        else:
            details_form = AccountDetailsForm(request.POST, instance=request.user, prefix="details")
            if details_form.is_valid():
                details_form.save()
                messages.success(request, "Your account details have been saved.")
                return redirect("account_details")
    return TemplateResponse(
        request,
        "home/account_details.html",
        {
            "account_section": "details",
            "details_form": details_form,
            "password_form": password_form,
        },
    )


class CustomerLoginView(LoginView):
    template_name = "home/account_login.html"
    redirect_authenticated_user = True
    extra_context = {"active_tab": "login"}


def register(request):
    if request.user.is_authenticated:
        return redirect(request.GET.get("next") or "shop")
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = ""
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(next_url or "shop")
    else:
        form = CustomerRegistrationForm()
    return TemplateResponse(
        request,
        "home/account_login.html",
        {"form": form, "next": next_url, "active_tab": "register"},
    )


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(
        ProductPage.objects.live().public(),
        pk=product_id,
    )
    if not product.is_available:
        return redirect(product.url)

    session_cart = _session_cart(request)
    key = str(product.pk)
    try:
        current_quantity = max(0, int(session_cart.get(key, 0)))
    except (TypeError, ValueError):
        current_quantity = 0
    quantity = _bounded_quantity(request.POST.get("quantity", 1))
    session_cart[key] = min(99, current_quantity + quantity)
    request.session[CART_SESSION_KEY] = session_cart
    return redirect("cart")


@require_POST
def cart_update(request, product_id):
    get_object_or_404(ProductPage.objects.live().public(), pk=product_id)
    session_cart = _session_cart(request)
    key = str(product_id)
    if key in session_cart:
        session_cart[key] = _bounded_quantity(request.POST.get("quantity", 1))
        request.session[CART_SESSION_KEY] = session_cart
    return redirect("cart")


@require_POST
def cart_remove(request, product_id):
    session_cart = _session_cart(request)
    session_cart.pop(str(product_id), None)
    request.session[CART_SESSION_KEY] = session_cart
    return redirect("cart")


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