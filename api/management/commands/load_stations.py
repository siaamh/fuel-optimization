import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import FuelStation


INPUT_FILE = os.path.join(
    os.path.dirname(__file__),  # commands/
    '..', '..', '..', '..', '..', # back up to project root
    'fuel_stations_geocoded.csv'
)


class Command(BaseCommand):
    help = "Load geocoded fuel stations from CSV into the database (MySQL)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            default=None,
            help='Path to the geocoded CSV file. Defaults to fuel_stations_geocoded.csv in project root.',
        )

    def handle(self, *args, **options):
        csv_path = options['csv'] or os.path.abspath(INPUT_FILE)

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"CSV not found: {csv_path}"))
            return

        self.stdout.write(f"Reading {csv_path} ...")

        created = 0
        updated = 0
        skipped = 0

        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"Found {len(rows)} rows. Loading ...")

        with transaction.atomic():
            for row in rows:

                # Skip rows without valid coordinates
                if row.get('Geocoding Status', '').strip() != 'success':
                    skipped += 1
                    continue

                try:
                    lat = float(row['Latitude'])
                    lon = float(row['Longitude'])
                    price = float(row['Retail Price'])
                    opis_id = int(row['OPIS Truckstop ID'])
                    rack_id = int(row['Rack ID'])
                except (ValueError, KeyError):
                    skipped += 1
                    continue

                obj, was_created = FuelStation.objects.update_or_create(
                    opis_id=opis_id,
                    defaults={
                        'name': row.get('Truckstop Name', '').strip(),
                        'address': row.get('Address', '').strip(),
                        'city': row.get('City', '').strip(),
                        'state': row.get('State', '').strip(),
                        'rack_id': rack_id,
                        'retail_price': price,
                        'latitude': lat,
                        'longitude': lon,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created}  Updated: {updated}  Skipped: {skipped}"
        ))
