from django.db import migrations


def update_hero_slide_cta_anchors(apps, schema_editor):
    HomePageHeroSlide = apps.get_model("home", "HomePageHeroSlide")
    database = schema_editor.connection.alias
    HomePageHeroSlide.objects.using(database).filter(
        cta_url__in=["#products", "#new-arrivals"]
    ).update(cta_url="#best-selling")


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0013_homepageheroslide"),
    ]

    operations = [
        migrations.RunPython(update_hero_slide_cta_anchors, migrations.RunPython.noop),
    ]