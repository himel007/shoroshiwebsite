import uuid

from django.db import migrations


def _next_child_path(Page, parent):
    children = Page.objects.filter(
        path__startswith=parent.path, depth=parent.depth + 1
    ).order_by("-path")
    if children.exists():
        last = children.first().path
        step = int(last[-4:]) + 1
    else:
        step = 1
    return parent.path + "{:04d}".format(step)


def create_page(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    HomePage = apps.get_model("home.HomePage")
    PrivacyPolicyPage = apps.get_model("home.PrivacyPolicyPage")

    homepage = HomePage.objects.filter(slug="home", depth=2).first()
    if homepage is None:
        return
    home_page = Page.objects.get(pk=homepage.pk)
    locale_id = home_page.locale_id

    if Page.objects.filter(slug="privacy", path__startswith=home_page.path).exists():
        return

    privacy_ct, _ = ContentType.objects.get_or_create(
        model="privacypolicypage", app_label="home"
    )

    PrivacyPolicyPage.objects.create(
        title="Privacy Policy",
        draft_title="Privacy Policy",
        slug="privacy",
        content_type=privacy_ct,
        path=_next_child_path(Page, home_page),
        depth=home_page.depth + 1,
        numchild=0,
        url_path=home_page.url_path + "privacy/",
        locale_id=locale_id,
        translation_key=uuid.uuid4(),
        live=True,
        has_unpublished_changes=False,
    )
    Page.objects.filter(pk=home_page.pk).update(numchild=home_page.numchild + 1)


def remove_page(apps, schema_editor):
    Page = apps.get_model("wagtailcore.Page")
    Page.objects.filter(slug="privacy", depth=3).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0023_privacypolicypage"),
    ]

    operations = [
        migrations.RunPython(create_page, remove_page),
    ]
