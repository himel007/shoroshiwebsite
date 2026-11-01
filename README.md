# Shoroshi Storefront

A Django and Wagtail foundation for Shoroshi's furniture e-commerce website.
The initial setup provides the CMS and local development environment; payments,
customer accounts, and order placement are not implemented yet.

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
commercial template. Adapt only the assets permitted by its license. The Shoroshi
logo is stored in `home/static/images/shoroshi-logo.png`.

## GitHub

This project is initialized as a local Git repository. Create a **private**
GitHub repository before pushing, and do not commit commercial template source,
secrets, the local database, or the virtual environment.
