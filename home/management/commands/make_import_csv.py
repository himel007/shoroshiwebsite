"""Scaffold a product-import CSV from a folder of images.

Given a folder of product photos, this writes a CSV with one row per image,
pre-filling the `image` column and a best-guess `title` and `sku` from each
filename. You then open the CSV, fill in price/description/stock/etc., and
feed it to `import_products`.

Usage:
    python manage.py make_import_csv --images-dir path/to/images --output products.csv

Options:
    --images-dir DIR   Folder containing the product photos (required).
    --output FILE      Where to write the CSV (default: products.csv in the images folder).
    --default-stock N  Value to pre-fill the stock column with (default: blank).
    --category NAME    Value to pre-fill the category column with (default: blank).
    --overwrite        Allow overwriting an existing output file.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

# Keep this list in step with import_products.REQUIRED_COLUMNS + optional ones.
COLUMNS = [
    "title",
    "category",
    "sku",
    "price",
    "image",
    "description",
    "fabric_details",
    "colour",
    "work_details",
    "measurements",
    "care_instructions",
    "is_available",
    "stock",
    "is_featured",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _title_from_filename(stem):
    text = stem.replace("_", " ").replace("-", " ")
    text = " ".join(text.split())  # collapse repeated spaces
    return text.title()


def _sku_from_filename(stem):
    return slugify(stem).upper().replace("-", "-") or "SKU"


class Command(BaseCommand):
    help = "Create a product-import CSV skeleton from a folder of images."

    def add_arguments(self, parser):
        parser.add_argument("--images-dir", required=True)
        parser.add_argument("--output", default=None)
        parser.add_argument("--default-stock", default="")
        parser.add_argument("--category", default="")
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **options):
        images_dir = Path(options["images_dir"])
        if not images_dir.is_dir():
            raise CommandError(f"Images folder not found: {images_dir}")

        output = Path(options["output"]) if options["output"] else images_dir / "products.csv"
        if output.exists() and not options["overwrite"]:
            raise CommandError(
                f"{output} already exists. Pass --overwrite to replace it."
            )

        images = sorted(
            p for p in images_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not images:
            raise CommandError(f"No image files found in {images_dir}.")

        seen_skus = {}
        rows = []
        for path in images:
            stem = path.stem
            sku = _sku_from_filename(stem)
            # Guarantee unique SKUs even if two filenames slugify the same.
            if sku in seen_skus:
                seen_skus[sku] += 1
                sku = f"{sku}-{seen_skus[sku]}"
            else:
                seen_skus[sku] = 1
            rows.append(
                {
                    "title": _title_from_filename(stem),
                    "category": options["category"],
                    "sku": sku,
                    "price": "",
                    "image": path.name,
                    "description": "",
                    "fabric_details": "",
                    "colour": "",
                    "work_details": "",
                    "measurements": "",
                    "care_instructions": "",
                    "is_available": "yes",
                    "stock": options["default_stock"],
                    "is_featured": "no",
                }
            )

        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows to {output}. "
                "Fill in price/description/etc., then run import_products."
            )
        )
