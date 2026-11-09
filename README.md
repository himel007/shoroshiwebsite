# Shoroshi Storefront

A Django and Wagtail foundation for SHOROSHI (ষোড়শী), a premium Bangladeshi
traditional fashion brand. The homepage is being adapted from the supplied
Helendo template and now includes a Wagtail-managed product catalog, category
filters, product detail pages, a session shopping bag, customer login and
registration, and a Cash on Delivery checkout. Online payment gateways are not
implemented yet.

## Requirements

- Python 3.9
- Git

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` for the site and `http://127.0.0.1:8000/admin/`
for Wagtail CMS.

## Manage categories

Product categories are managed in Wagtail admin under **Snippets -> Shop ->
Product categories** (four defaults are provided: Muslin, Balaka, Endi, and
Joyosree Silk). Add, rename, reorder, or delete categories there; the slug is
filled in from the name automatically. A category that still has products
cannot be deleted. When adding a product, pick its category from the dropdown.

## Add products

In Wagtail, create a Product page under the homepage. Add a verified product
name, category, SKU, price in BDT, product image, fabric and design details,
care instructions, and availability, then publish it. Published products appear
in the homepage grid and category filters. No sample products are preloaded.

## Checkout and orders

Customers must log in or register (`/account/login/`, `/account/register/`)
before checking out. Checkout offers Cash on Delivery only.

Before taking orders, open Wagtail admin -> **Shop -> Delivery zones** and add
your delivery areas with their charges (for example, Inside Dhaka and Outside
Dhaka). No delivery charges are preloaded; checkout stays closed until at least
one active zone exists.

Placed orders appear under **Shop -> Orders**. Use the inspect view to see the
customer's address and items, and the edit view to change the order status or
add an internal staff note.

## Contact, FAQ, and footer links

A **Contact** page (`/contact/`) and an **FAQ** page (`/faq/`) are created
automatically and are editable in Wagtail admin (both start with PLACEHOLDER
text). Edit the Contact page for your address, phone, email, hours, and an
optional Google Maps embed. Edit the FAQ page to change the questions and
answers.

The footer shows **FAQ**, **Contact**, and **Track order** links, plus
**WhatsApp, Facebook, Instagram, and Send us mail** icons. Set those in Wagtail
admin under **Settings -> Contact & social links**; each icon only appears once
its value is filled in, so no contact detail is invented.

## Template and brand assets

The supplied Helendo ThemeForest archive is kept outside Git because it is a
commercial template. Place the zip in `theme-source/` (ignored by Git) and
extract it there for reference. Adapt only assets permitted by its license. The Shoroshi
logo is in `home/static/images/shoroshi-logo.png`. Brand copy and colors follow
the supplied Shoroshi website brief; unconfirmed business details and products
must not be invented.

## GitHub

This project is initialized as a local Git repository. Create a **private**
GitHub repository before pushing, and do not commit commercial template source,
secrets, the local database, or the virtual environment.
