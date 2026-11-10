import csv
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class MakeImportCsvTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _touch(self, *names):
        for name in names:
            (self.dir / name).write_bytes(b"x")

    def _read(self, path):
        with open(path, newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_scaffolds_one_row_per_image_and_skips_non_images(self):
        self._touch("red-saree.jpg", "blue_kurti.PNG", "readme.txt")
        out = self.dir / "products.csv"
        call_command("make_import_csv", images_dir=str(self.dir), output=str(out),
                     default_stock="5", category="Saree")
        rows = self._read(out)
        self.assertEqual(len(rows), 2)
        by_image = {r["image"]: r for r in rows}
        self.assertIn("red-saree.jpg", by_image)
        self.assertEqual(by_image["red-saree.jpg"]["title"], "Red Saree")
        self.assertEqual(by_image["red-saree.jpg"]["stock"], "5")
        self.assertEqual(by_image["red-saree.jpg"]["category"], "Saree")
        self.assertEqual(by_image["red-saree.jpg"]["is_available"], "yes")

    def test_duplicate_skus_are_made_unique(self):
        self._touch("saree.jpg", "saree.png")
        out = self.dir / "products.csv"
        call_command("make_import_csv", images_dir=str(self.dir), output=str(out))
        skus = sorted(r["sku"] for r in self._read(out))
        self.assertEqual(len(set(skus)), 2)

    def test_refuses_to_overwrite_without_flag(self):
        self._touch("a.jpg")
        out = self.dir / "products.csv"
        call_command("make_import_csv", images_dir=str(self.dir), output=str(out))
        with self.assertRaises(CommandError):
            call_command("make_import_csv", images_dir=str(self.dir), output=str(out))
        # With the flag it succeeds.
        call_command("make_import_csv", images_dir=str(self.dir), output=str(out),
                     overwrite=True)

    def test_errors_when_no_images(self):
        with self.assertRaises(CommandError):
            call_command("make_import_csv", images_dir=str(self.dir),
                         output=str(self.dir / "products.csv"))
