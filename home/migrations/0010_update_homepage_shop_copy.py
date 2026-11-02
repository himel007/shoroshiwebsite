from django.db import migrations


def update_homepage_for_shop(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    HomePage.objects.filter(slug="home", depth=2).update(
        hero_description="Traditional sarees, chosen for your next occasion.",
        hero_cta_url="#products",
        hero_secondary_cta_url="#categories",
    )


def restore_homepage_copy(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    HomePage.objects.filter(slug="home", depth=2).update(
        hero_description=(
            "Discover the beauty of traditional Bengali fashion with Shoroshi. "
            "Explore our thoughtfully curated collection of luxurious sarees, "
            "elegant three-piece outfits, and timeless accessories."
        ),
        hero_cta_url="#new-arrivals",
        hero_secondary_cta_url="#collections",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0009_alter_homepage_hero_description_and_more"),
    ]

    operations = [
        migrations.RunPython(update_homepage_for_shop, restore_homepage_copy),
    ]