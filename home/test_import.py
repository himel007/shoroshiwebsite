import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from PIL import Image as PillowImage

from home.models import ProductCategory, ProductPage


CSV_HEADER = (
    "title,category,sku,price,image,description,fabric_details,colour,"
    "work_details,measurements,care_instructions,is_available,is_featured\n"
)


class ImportProductsTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        # one real image file the CSV can reference
        PillowImage.new("RGB", (10, 10), color="blue").save(self.dir / "saree.png")

    def _write_csv(self, *rows):
        path = self.dir / "products.csv"
        path.write_text(CSV_HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
        return path

    def _run(self, path, **kwargs):
        out, err = StringIO(), StringIO()
        call_command("import_products", str(path), stdout=out, stderr=err, **kwargs)
        return out.getvalue(), err.getvalue()

    def test_imports_a_product_and_creates_category(self):
        csv_path = self._write_csv(
            "Muslin Saree,Jamdani,JAM-1,12500,saree.png,A fine saree,Muslin,Red,Hand work,5.5m,Dry clean,yes,no"
        )
        out, _ = self._run(csv_path)
        self.assertIn("Created 1", out)
        product = ProductPage.objects.get(sku="JAM-1")
        self.assertEqual(product.title, "Muslin Saree")
        self.assertEqual(product.price, __import__("decimal").Decimal("12500"))
        self.assertTrue(product.is_available)
        self.assertEqual(product.category.name, "Jamdani")
        self.assertTrue(product.live)

    def test_reuses_existing_category_by_name_or_slug(self):
        existing = ProductCategory.objects.get(slug="muslin-silk")
        csv_path = self._write_csv(
            "A,Muslin Silk,SK-1,100,saree.png,d,f,c,w,,care,yes,no",
            "B,muslin-silk,SK-2,100,saree.png,d,f,c,w,,care,yes,no",
        )
        self._run(csv_path)
        self.assertEqual(ProductPage.objects.get(sku="SK-1").category, existing)
        self.assertEqual(ProductPage.objects.get(sku="SK-2").category, existing)
        self.assertEqual(ProductCategory.objects.filter(slug="muslin-silk").count(), 1)

    def test_dry_run_saves_nothing(self):
        csv_path = self._write_csv(
            "Muslin Saree,Jamdani,JAM-1,12500,saree.png,d,f,c,w,,care,yes,no"
        )
        out, _ = self._run(csv_path, dry_run=True)
        self.assertIn("DRY RUN", out)
        self.assertFalse(ProductPage.objects.filter(sku="JAM-1").exists())
        self.assertFalse(ProductCategory.objects.filter(name="Jamdani").exists())

    def test_duplicate_sku_is_skipped_then_updated_with_flag(self):
        row = "Name One,Jamdani,DUP-1,100,saree.png,d,f,c,w,,care,yes,no"
        csv_path = self._write_csv(row)
        self._run(csv_path)
        # Re-running without --update skips it.
        out, _ = self._run(csv_path)
        self.assertIn("skipped 1", out)
        self.assertEqual(ProductPage.objects.filter(sku="DUP-1").count(), 1)
        # With --update and a changed title, it updates in place.
        csv2 = self._write_csv(
            "Name Two,Jamdani,DUP-1,250,saree.png,d,f,c,w,,care,yes,no"
        )
        out, _ = self._run(csv2, update=True)
        self.assertIn("updated 1", out)
        product = ProductPage.objects.get(sku="DUP-1")
        self.assertEqual(product.title, "Name Two")
        self.assertEqual(product.price, __import__("decimal").Decimal("250"))

    def test_bad_rows_are_reported_and_others_still_import(self):
        csv_path = self._write_csv(
            "Good,Jamdani,OK-1,100,saree.png,d,f,c,w,,care,yes,no",
            "No Price,Jamdani,BAD-1,notnum,saree.png,d,f,c,w,,care,yes,no",
            "Missing Image,Jamdani,BAD-2,100,nope.png,d,f,c,w,,care,yes,no",
        )
        out, err = self._run(csv_path)
        self.assertIn("Created 1", out)
        self.assertIn("errors 2", out)
        self.assertIn("BAD-1", err)
        self.assertIn("BAD-2", err)
        self.assertTrue(ProductPage.objects.filter(sku="OK-1").exists())
        self.assertFalse(ProductPage.objects.filter(sku="BAD-1").exists())

    def test_missing_required_column_fails_fast(self):
        bad = self.dir / "bad.csv"
        bad.write_text("title,sku,price\nA,SK,100\n", encoding="utf-8")
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            self._run(bad)
