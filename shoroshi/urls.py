from django.conf import settings
from django.urls import include, path
from django.contrib import admin

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
    path("wishlist/", home_views.wishlist, name="wishlist"),
    path("wishlist/add/<int:product_id>/", home_views.wishlist_add, name="wishlist_add"),
    path("wishlist/remove/<int:product_id>/", home_views.wishlist_remove, name="wishlist_remove"),
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
