# Shoroshi Storefront

A Django and Wagtail foundation for SHOROSHI (ষোড়শী), a premium Bangladeshi
traditional fashion brand. The homepage is being adapted from the supplied
Helendo template. Product catalog, customer accounts, checkout, and payments
are not implemented yet.

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

## Template and brand assets

The supplied Helendo ThemeForest archive is kept outside Git because it is a
commercial template. Adapt only assets permitted by its license. The Shoroshi
logo is in `home/static/images/shoroshi-logo.png`. Brand copy and colors follow
the supplied Shoroshi website brief; unconfirmed business details and products
must not be invented.

## GitHub

This project is initialized as a local Git repository. Create a **private**
GitHub repository before pushing, and do not commit commercial template source,
secrets, the local database, or the virtual environment.
