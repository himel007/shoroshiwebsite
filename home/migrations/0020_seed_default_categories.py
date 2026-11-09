from django.db import migrations

DEFAULTS = [
    ("muslin-silk", "Muslin Silk"),
    ("balaka-silk", "Balaka Silk"),
    ("endi-silk", "Endi Silk"),
    ("joyosree-silk", "Joyosree Silk"),
]


def seed(apps, schema_editor):
    ProductCategory = apps.get_model("home", "ProductCategory")
    for order, (slug, name) in enumerate(DEFAULTS, start=1):
        ProductCategory.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "sort_order": order},
        )


def unseed(apps, schema_editor):
    ProductCategory = apps.get_model("home", "ProductCategory")
    ProductCategory.objects.filter(slug__in=[s for s, _ in DEFAULTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0019_productcategory_alter_productpage_category"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
