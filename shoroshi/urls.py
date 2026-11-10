from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.contrib.auth.views import LogoutView

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from home import views as home_views
from search import views as search_views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("shop/", home_views.shop, name="shop"),
    path("cart/", home_views.cart, name="cart"),
    path("cart/add/<int:product_id>/", home_views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", home_views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", home_views.cart_remove, name="cart_remove"),
    path("track-order/", home_views.track_order, name="track_order"),
    path("wishlist/", home_views.wishlist, name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", home_views.wishlist_toggle, name="wishlist_toggle"),
    path("checkout/", home_views.checkout, name="checkout"),
    path("checkout/complete/<int:order_id>/", home_views.checkout_complete, name="checkout_complete"),
    path("invoice/<int:order_id>/", home_views.invoice, name="invoice"),
    # Social login (Google) by django-allauth. Included BEFORE the custom
    # account/* routes so the storefront's own account_login / account_logout
    # names keep priority in reverse().
    path("accounts/", include("allauth.urls")),
    path("account/", home_views.account_dashboard, name="account_dashboard"),
    path("account/orders/", home_views.account_orders, name="account_orders"),
    path("account/orders/<int:order_id>/", home_views.account_order_detail, name="account_order_detail"),
    path("account/details/", home_views.account_details, name="account_details"),
    path("account/login/", home_views.CustomerLoginView.as_view(), name="account_login"),
    path("account/register/", home_views.register, name="account_register"),
    path("account/logout/", LogoutView.as_view(next_page="/"), name="account_logout"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
