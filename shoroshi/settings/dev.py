from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

STORAGES["staticfiles"] = {
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-qanw+uuqh7theey2jewnz^fy+iz6&e_rlkg+3og-dydeacewzo"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


try:
    from .local import *
except ImportError:
    pass
