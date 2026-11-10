from decimal import Decimal

from django.core.management.base import BaseCommand

from home.models import DeliveryZone


# Steadfast's standard 3-tier coverage. These charges are DEFAULTS — confirm
# your own negotiated rates in Wagtail admin (Snippets > Shop > Delivery zones).
STEADFAST_ZONES = [
    {
        "name": "Inside Dhaka",
        "charge": Decimal("60.00"),
        "description": "Dhaka city — delivery in 1–2 days.",
        "sort_order": 1,
    },
    {
        "name": "Dhaka Sub-area",
        "charge": Decimal("80.00"),
        "description": "Savar, Keraniganj, Narayanganj & nearby — 1–3 days.",
        "sort_order": 2,
    },
    {
        "name": "Outside Dhaka",
        "charge": Decimal("120.00"),
        "description": "Anywhere else in Bangladesh — 2–4 days.",
        "sort_order": 3,
    },
]


class Command(BaseCommand):
    help = "Seed the standard Steadfast delivery zones (does not overwrite existing ones)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-charges",
            action="store_true",
            help="Also reset the charge/description of existing zones to the defaults.",
        )

    def handle(self, *args, **options):
        created, updated, skipped = 0, 0, 0
        for data in STEADFAST_ZONES:
            zone, was_created = DeliveryZone.objects.get_or_create(
                name=data["name"],
                defaults={
                    "charge": data["charge"],
                    "description": data["description"],
                    "sort_order": data["sort_order"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {zone.name} — BDT {zone.charge}"))
            elif options["reset_charges"]:
                zone.charge = data["charge"]
                zone.description = data["description"]
                zone.sort_order = data["sort_order"]
                zone.save(update_fields=["charge", "description", "sort_order"])
                updated += 1
                self.stdout.write(f"Reset: {zone.name} — BDT {zone.charge}")
            else:
                skipped += 1
                self.stdout.write(f"Kept existing: {zone.name} — BDT {zone.charge}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {created} created, {updated} reset, {skipped} kept. "
                "Review charges in admin: Snippets > Shop > Delivery zones."
            )
        )
