# Shoroshi Storefront Instructions

- This is a Django 4.2 and Wagtail 6.4 project, currently compatible with Python 3.9.
- Keep storefront content editable through Wagtail page models where practical.
- SHOROSHI (ষোড়শী) is a premium Bangladeshi traditional fashion brand; use the supplied website brief as the content source of truth.
- Use the brief's warm ivory (#F5EFE5), deep brown (#30251F), antique gold (#B38A55), and wine (#7B303B) palette and the existing Shoroshi logo.
- Do not invent product information, prices, inventory, customer reviews, business contacts, delivery charges, or policy terms.
- Keep the original commercial Helendo template archive out of Git and only adapt assets permitted by its license.
- Checkout is Cash on Delivery only, requires a customer login, and uses delivery zones whose charges staff set in Wagtail admin. Do not add online payment processing until explicitly requested and the business details are confirmed.
- Keep Django secrets and local databases out of version control.
- Keep the explanatory comment in `manage.py`'s `main()` entry point.
