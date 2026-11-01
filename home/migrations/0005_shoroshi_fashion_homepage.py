from django.db import migrations, models


def set_fashion_homepage_copy(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    HomePage.objects.filter(slug="home", depth=2).update(
        title="Elegance That Lives Beyond Time.",
        draft_title="Elegance That Lives Beyond Time.",
        seo_title="Shoroshi – Premium Sarees & Traditional Fashion Bangladesh",
        search_description=(
            "Discover elegant sarees, hand-stitched collections, silk sarees, "
            "three-piece outfits, and traditional accessories at Shoroshi. "
            "Celebrate Bengali fashion with timeless elegance. Shop online in Bangladesh."
        ),
        hero_eyebrow="CELEBRATING THE BEAUTY OF TRADITION",
        hero_description=(
            "Discover the beauty of traditional Bengali fashion with Shoroshi. "
            "Explore our thoughtfully curated collection of luxurious sarees, "
            "elegant three-piece outfits, and timeless accessories."
        ),
        hero_cta_text="SHOP NOW",
        hero_cta_url="#new-arrivals",
        hero_secondary_cta_text="EXPLORE COLLECTION",
        hero_secondary_cta_url="#collections",
    )


def restore_furniture_homepage_copy(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    HomePage.objects.filter(slug="home", depth=2).update(
        title="Shoroshi",
        draft_title="Shoroshi",
        seo_title="",
        search_description="",
        hero_eyebrow="Shoroshi Bangladesh",
        hero_description="Furniture for the spaces you call home.",
        hero_cta_text="Explore collection",
        hero_cta_url="#collections",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0004_update_homepage_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepage",
            name="hero_secondary_cta_text",
            field=models.CharField(blank=True, default="EXPLORE COLLECTION", max_length=40),
        ),
        migrations.AddField(
            model_name="homepage",
            name="hero_secondary_cta_url",
            field=models.CharField(blank=True, default="#collections", max_length=200),
        ),
        migrations.AddField(
            model_name="homepage",
            name="instagram_url",
            field=models.URLField(blank=True),
        ),
        migrations.RunPython(set_fashion_homepage_copy, restore_furniture_homepage_copy),
    ]