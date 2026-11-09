import uuid

from django.db import migrations

FAQ_PLACEHOLDERS = [
    ("PLACEHOLDER — How do I place an order?",
     "<p>PLACEHOLDER — replace this answer in Wagtail admin with your real ordering steps.</p>"),
    ("PLACEHOLDER — What payment methods do you accept?",
     "<p>PLACEHOLDER — we currently offer Cash on Delivery. Edit this answer in Wagtail admin.</p>"),
    ("PLACEHOLDER — How long does delivery take?",
     "<p>PLACEHOLDER — add your delivery timelines for inside and outside Dhaka in Wagtail admin.</p>"),
    ("PLACEHOLDER — What is your return policy?",
     "<p>PLACEHOLDER — add your return and exchange policy in Wagtail admin.</p>"),
]


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


def create_pages(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    HomePage = apps.get_model("home.HomePage")
    ContactPage = apps.get_model("home.ContactPage")
    FAQPage = apps.get_model("home.FAQPage")
    FAQItem = apps.get_model("home.FAQItem")

    homepage = HomePage.objects.filter(slug="home", depth=2).first()
    if homepage is None:
        return
    home_page = Page.objects.get(pk=homepage.pk)
    locale_id = home_page.locale_id

    contact_ct, _ = ContentType.objects.get_or_create(model="contactpage", app_label="home")
    faq_ct, _ = ContentType.objects.get_or_create(model="faqpage", app_label="home")

    created = 0

    if not Page.objects.filter(slug="contact", path__startswith=home_page.path).exists():
        ContactPage.objects.create(
            title="Contact",
            draft_title="Contact",
            slug="contact",
            content_type=contact_ct,
            path=_next_child_path(Page, home_page),
            depth=home_page.depth + 1,
            numchild=0,
            url_path=home_page.url_path + "contact/",
            locale_id=locale_id,
            translation_key=uuid.uuid4(),
            live=True,
            has_unpublished_changes=False,
        )
        created += 1

    if not Page.objects.filter(slug="faq", path__startswith=home_page.path).exists():
        home_page.refresh_from_db()
        faq = FAQPage.objects.create(
            title="FAQ",
            draft_title="FAQ",
            slug="faq",
            content_type=faq_ct,
            path=_next_child_path(Page, home_page),
            depth=home_page.depth + 1,
            numchild=0,
            url_path=home_page.url_path + "faq/",
            locale_id=locale_id,
            translation_key=uuid.uuid4(),
            live=True,
            has_unpublished_changes=False,
        )
        for order, (question, answer) in enumerate(FAQ_PLACEHOLDERS):
            FAQItem.objects.create(page=faq, sort_order=order, question=question, answer=answer)
        created += 1

    if created:
        Page.objects.filter(pk=home_page.pk).update(numchild=home_page.numchild + created)


def remove_pages(apps, schema_editor):
    Page = apps.get_model("wagtailcore.Page")
    Page.objects.filter(slug__in=["contact", "faq"], depth=3).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0017_contactpage_faqpage_sitecontactsettings_faqitem"),
    ]

    operations = [
        migrations.RunPython(create_pages, remove_pages),
    ]
