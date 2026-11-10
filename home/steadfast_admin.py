"""Wagtail admin views to dispatch an order to Steadfast and refresh its status."""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from . import steadfast
from .models import Order


def _require_change(user):
    return user.is_authenticated and user.has_perm("home.change_order")


def _back_to_order(order):
    try:
        return redirect(
            reverse("wagtailsnippets_home_order:inspect", args=[order.pk])
        )
    except Exception:
        return redirect(reverse("wagtailsnippets_home_order:list"))


@login_required
@require_http_methods(["GET", "POST"])
def dispatch_to_steadfast(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if not _require_change(request.user):
        messages.error(request, "You do not have permission to dispatch orders.")
        return _back_to_order(order)

    if order.is_dispatched:
        messages.info(
            request,
            f"Order {order.number} was already sent to Steadfast "
            f"(consignment {order.courier_consignment_id}).",
        )
        return _back_to_order(order)

    default_items = ", ".join(
        f"{item.product_title} × {item.quantity}" for item in order.items.all()
    )

    if request.method == "POST":
        if not steadfast.is_configured():
            messages.error(
                request,
                "Steadfast API keys are not configured on the server. "
                "Set STEADFAST_API_KEY and STEADFAST_SECRET_KEY first.",
            )
            return _back_to_order(order)
        try:
            cod_amount = Decimal(request.POST.get("cod_amount", "")).quantize(Decimal("0.01"))
            if cod_amount < 0:
                raise InvalidOperation
        except (InvalidOperation, ArithmeticError):
            messages.error(request, "Enter a valid COD amount (0 or more).")
            return redirect(reverse("steadfast_dispatch", args=[order.pk]))

        item_description = request.POST.get("item_description", "").strip() or default_items
        note = request.POST.get("note", "").strip()

        try:
            consignment = steadfast.create_order(
                invoice=order.number,
                recipient_name=order.full_name,
                recipient_phone=order.phone,
                recipient_address=(
                    f"{order.address_line1}, "
                    f"{order.address_line2 + ', ' if order.address_line2 else ''}"
                    f"{order.city}, {order.district}"
                    f"{' ' + order.postcode if order.postcode else ''}"
                ),
                cod_amount=cod_amount,
                note=note,
                item_description=item_description,
            )
        except steadfast.SteadfastError as exc:
            messages.error(request, str(exc))
            return _back_to_order(order)

        order.courier_consignment_id = str(consignment.get("consignment_id", ""))
        order.courier_tracking_code = consignment.get("tracking_code", "") or ""
        order.courier_status = consignment.get("status", "") or ""
        order.courier_cod_amount = cod_amount
        order.dispatched_at = timezone.now()
        if order.status in (Order.STATUS_PENDING, "confirmed"):
            order.status = "shipped"
        order.save(update_fields=[
            "courier_consignment_id", "courier_tracking_code", "courier_status",
            "courier_cod_amount", "dispatched_at", "status",
        ])
        messages.success(
            request,
            f"Order {order.number} sent to Steadfast. Tracking code "
            f"{order.courier_tracking_code or '—'}, COD ৳{cod_amount}.",
        )
        return _back_to_order(order)

    return TemplateResponse(
        request,
        "home/admin/steadfast_dispatch.html",
        {
            "order": order,
            "cod_default": order.cod_amount_due,
            "item_default": default_items,
            "configured": steadfast.is_configured(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def refresh_steadfast_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if not _require_change(request.user):
        messages.error(request, "You do not have permission to update orders.")
        return _back_to_order(order)
    if not order.is_dispatched:
        messages.info(request, f"Order {order.number} has not been dispatched yet.")
        return _back_to_order(order)
    try:
        status = steadfast.get_status_by_consignment(order.courier_consignment_id)
    except steadfast.SteadfastError as exc:
        messages.error(request, str(exc))
        return _back_to_order(order)
    order.courier_status = status
    order.save(update_fields=["courier_status"])
    messages.success(
        request,
        f"Order {order.number} status updated: {order.courier_status_label}.",
    )
    return _back_to_order(order)
