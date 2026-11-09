from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from wagtail.images import get_image_model
from wagtail.models import Collection


class Command(BaseCommand):
    help = "Import JPG and JPEG photos into the Wagtail 'JPG Shoroshi' collection."

    def add_arguments(self, parser):
        parser.add_argument("source_directory", type=Path)

    def handle(self, *args, **options):
        source_directory = options["source_directory"].expanduser()
        if not source_directory.is_dir():
            raise CommandError(f"Source directory does not exist: {source_directory}")

        source_images = sorted(
            path
            for path in source_directory.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
        )
        if not source_images:
            raise CommandError(f"No JPG or JPEG files found in {source_directory}")

        collection = Collection.objects.filter(name="JPG Shoroshi").first()
        if collection is None:
            collection = Collection.get_first_root_node().add_child(
                instance=Collection(name="JPG Shoroshi")
            )

        image_model = get_image_model()
        source_titles = [path.stem for path in source_images]
        existing_titles = set(
            image_model.objects.filter(
                collection=collection,
                title__in=source_titles,
            ).values_list("title", flat=True)
        )

        imported = 0
        skipped = 0
        for path in source_images:
            if path.stem in existing_titles:
                skipped += 1
                continue

            image = image_model(title=path.stem, collection=collection)
            try:
                with path.open("rb") as source_file:
                    image.file.save(path.name, File(source_file), save=True)
            except Exception as error:
                raise CommandError(f"Could not import {path.name}: {error}") from error

            imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported} images into '{collection.name}'; skipped {skipped} existing images."
            )
        )