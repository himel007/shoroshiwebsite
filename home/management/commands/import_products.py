"""Bulk-import products from a CSV file and a folder of images.

Usage:
    python manage.py import_products path/to/products.csv --images-dir path/to/images

Options:
    --images-dir DIR   Folder containing the image files named in the CSV (default: same
                       folder as the CSV).
    --dry-run          Validate every row and report problems, but save nothing.
    --update           Update an existing product (matched by SKU) instead of skipping it.

The CSV columns are described in product_import_template.csv. Category may be given by
name or slug; a category that does not exist yet is created automatically.
"""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from wagtail.images import get_image_model
from wagtail.models import Page

from home.models import HomePage, ProductCategory, ProductPage

REQUIRED_COLUMNS = [
    "title",
    "category",
    "sku",
    "price",
    "image",
    "description",
    "fabric_details",
    "colour",
    "work_details",
    "care_instructions",
]
TRUE_VALUES = {"1", "true", "yes", "y", "available", "in stock"}


def _as_bool(value):
    return str(value or "").strip().lower() in TRUE_VALUES


class Command(BaseCommand):
    help = "Bulk-import products from a CSV file and a folder of images."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--images-dir", default=None)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--update", action="store_true")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.is_file():
            raise CommandError(f"CSV file not found: {csv_path}")
        images_dir = Path(options["images_dir"]) if options["images_dir"] else csv_path.parent
        if not images_dir.is_dir():
            raise CommandError(f"Images folder not found: {images_dir}")

        homepage = HomePage.objects.live().first()
        if homepage is None:
            raise CommandError("No Home page found to add products under.")

        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise CommandError("CSV is missing required columns: " + ", ".join(missing))
            rows = list(reader)

        if not rows:
            raise CommandError("The CSV has no data rows.")

        dry_run = options["dry_run"]
        created = updated = skipped = 0
        errors = []

        for number, row in enumerate(rows, start=2):  # row 1 is the header
            try:
                if dry_run:
                    result = self._validate_row(row, images_dir, options["update"])
                else:
                    with transaction.atomic():
                        result = self._import_row(
                            row, homepage, images_dir, options["update"]
                        )
                if result == "created":
                    created += 1
                elif result == "updated":
                    updated += 1
                else:
                    skipped += 1
            except Exception as exc:  # noqa: BLE001 - report per-row and continue
                errors.append(f"Row {number} ({row.get('sku', '?')}): {exc}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes saved."))

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created}, updated {updated}, skipped {skipped}, errors {len(errors)}."
            )
        )
        for message in errors:
            self.stderr.write(self.style.ERROR(message))

    def _parse_row(self, row, images_dir):
        """Validate a row without writing anything. Returns (title, sku, price, path)."""
        title = (row.get("title") or "").strip()
        sku = (row.get("sku") or "").strip()
        if not title:
            raise ValueError("title is required")
        if not sku:
            raise ValueError("sku is required")

        try:
            price = Decimal((row.get("price") or "").strip())
        except (InvalidOperation, ValueError):
            raise ValueError(f"price '{row.get('price')}' is not a valid number")
        if price <= 0:
            raise ValueError("price must be greater than 0")

        if not (row.get("category") or "").strip():
            raise ValueError("category is required")

        filename = (row.get("image") or "").strip()
        if not filename:
            raise ValueError("image is required")
        path = images_dir / filename
        if not path.is_file():
            raise ValueError(f"image file not found: {filename}")

        return title, sku, price, path

    def _validate_row(self, row, images_dir, allow_update):
        title, sku, price, path = self._parse_row(row, images_dir)
        existing = ProductPage.objects.filter(sku=sku).exists()
        if existing and not allow_update:
            return "skipped"
        return "updated" if existing else "created"

    def _import_row(self, row, homepage, images_dir, allow_update):
        title, sku, price, image_path = self._parse_row(row, images_dir)

        existing = ProductPage.objects.filter(sku=sku).first()
        if existing and not allow_update:
            return "skipped"

        category = self._get_or_create_category(row.get("category"))
        image = self._create_image(image_path, title)

        fields = dict(
            category=category,
            sku=sku,
            price=price,
            product_image=image,
            description=(row.get("description") or "").strip(),
            fabric_details=(row.get("fabric_details") or "").strip(),
            colour=(row.get("colour") or "").strip(),
            work_details=(row.get("work_details") or "").strip(),
            measurements=(row.get("measurements") or "").strip(),
            care_instructions=(row.get("care_instructions") or "").strip(),
            is_available=_as_bool(row.get("is_available")),
            is_featured=_as_bool(row.get("is_featured")),
        )

        if existing:
            existing.title = title
            for key, value in fields.items():
                setattr(existing, key, value)
            existing.save_revision().publish()
            return "updated"

        product = ProductPage(title=title, **fields)
        homepage.add_child(instance=product)
        product.save_revision().publish()
        return "created"

    def _get_or_create_category(self, value):
        value = (value or "").strip()
        if not value:
            raise ValueError("category is required")
        slug = slugify(value)
        category = ProductCategory.objects.filter(slug=slug).first()
        if category is None:
            category = ProductCategory.objects.filter(name__iexact=value).first()
        if category is None:
            category = ProductCategory.objects.create(name=value)
        return category

    def _create_image(self, path, title):
        Image = get_image_model()
        with path.open("rb") as handle:
            image = Image(title=title)
            image.file = ImageFile(handle, name=path.name)
            image.save()
        return image
