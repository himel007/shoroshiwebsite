from django.utils.functional import SimpleLazyObject

from .models import WishlistItem


def wishlist(request):
    """Expose the logged-in customer's saved product ids as ``wishlist_ids``.

    Evaluated lazily, so pages that never show a heart button don't query it.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"wishlist_ids": frozenset()}
    return {
        "wishlist_ids": SimpleLazyObject(
            lambda: frozenset(
                WishlistItem.objects.filter(user=user).values_list("product_id", flat=True)
            )
        )
    }
