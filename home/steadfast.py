"""Thin client for the Steadfast Courier API (V1).

Docs: https://portal.packzy.com/api/v1

Only the pieces the storefront needs are implemented: create a consignment
and read its delivery status. Credentials come from settings (env vars):
STEADFAST_API_KEY, STEADFAST_SECRET_KEY, STEADFAST_BASE_URL.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 20  # seconds

# Delivery status values returned by Steadfast, mapped to customer-facing text.
DELIVERY_STATUS_LABELS = {
    "pending": "Pending pickup",
    "in_review": "In review",
    "hold": "On hold",
    "delivered": "Delivered",
    "partial_delivered": "Partially delivered",
    "cancelled": "Cancelled / returned",
    "unknown": "In transit",
    "delivered_approval_pending": "Delivered (confirming)",
    "partial_delivered_approval_pending": "Partially delivered (confirming)",
    "cancelled_approval_pending": "Cancelled (confirming)",
    "unknown_approval_pending": "In transit",
}


class SteadfastError(Exception):
    """Raised when the Steadfast API call fails or is misconfigured."""


def is_configured() -> bool:
    return bool(settings.STEADFAST_API_KEY and settings.STEADFAST_SECRET_KEY)


def status_label(value: str) -> str:
    if not value:
        return "Not dispatched"
    return DELIVERY_STATUS_LABELS.get(value, value.replace("_", " ").title())


def _headers() -> dict:
    return {
        "Api-Key": settings.STEADFAST_API_KEY,
        "Secret-Key": settings.STEADFAST_SECRET_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _url(path: str) -> str:
    return f"{settings.STEADFAST_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def create_order(*, invoice, recipient_name, recipient_phone, recipient_address,
                 cod_amount, note="", item_description="") -> dict:
    """Create a consignment. Returns the ``consignment`` dict from Steadfast.

    Raises SteadfastError on any failure. This request is never retried,
    because a duplicate could create a duplicate consignment.
    """
    if not is_configured():
        raise SteadfastError(
            "Steadfast API credentials are not set. Add STEADFAST_API_KEY and "
            "STEADFAST_SECRET_KEY to the environment."
        )

    payload = {
        "invoice": invoice,
        "recipient_name": recipient_name[:100],
        "recipient_phone": recipient_phone,
        "recipient_address": recipient_address[:250],
        "cod_amount": float(cod_amount),
        "note": note or "",
    }
    if item_description:
        payload["item_description"] = item_description

    try:
        response = requests.post(
            _url("create_order"), json=payload, headers=_headers(), timeout=TIMEOUT
        )
    except requests.RequestException as exc:
        logger.exception("Steadfast create_order network error")
        raise SteadfastError(f"Could not reach Steadfast: {exc}") from exc

    data = _parse(response)
    consignment = data.get("consignment")
    if response.status_code not in (200, 201) or not consignment:
        message = data.get("message") or f"HTTP {response.status_code}"
        raise SteadfastError(f"Steadfast rejected the order: {message}")
    return consignment


def get_status_by_consignment(consignment_id) -> str:
    """Return the current delivery_status string for a consignment id."""
    if not is_configured():
        raise SteadfastError("Steadfast API credentials are not set.")
    try:
        response = requests.get(
            _url(f"status_by_cid/{consignment_id}"),
            headers=_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SteadfastError(f"Could not reach Steadfast: {exc}") from exc

    data = _parse(response)
    status = data.get("delivery_status")
    if response.status_code != 200 or not status:
        message = data.get("message") or f"HTTP {response.status_code}"
        raise SteadfastError(f"Could not read status: {message}")
    return status


def _parse(response) -> dict:
    try:
        data = response.json()
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}
