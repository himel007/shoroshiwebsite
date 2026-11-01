from django.db import migrations


def update_homepage_title(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    HomePage.objects.filter(slug="home", depth=2).update(
        title="Shoroshi",
        draft_title="Shoroshi",
    )


def restore_homepage_title(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    HomePage.objects.filter(slug="home", depth=2).update(
        title="Home",
        draft_title="Home",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0003_homepage_hero_cta_text_homepage_hero_cta_url_and_more"),
    ]

    operations = [
        migrations.RunPython(update_homepage_title, restore_homepage_title),
    ]