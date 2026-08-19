import csv
import os
import time

import requests

from django.core.management.base import BaseCommand


INPUT_FILE = r"C:\Users\ASUS\Downloads\fuel-prices-for-be-assessment - fuel-prices-for-be-assessment.csv"

OUTPUT_FILE = "fuel_stations_geocoded.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

USER_AGENT = "fuel-optimization-assessment/1.0"


class Command(BaseCommand):
    help = "Geocode fuel station CSV and save latitude/longitude"

    def handle(self, *args, **options):

        if not os.path.exists(INPUT_FILE):
            self.stdout.write(
                self.style.ERROR(
                    f"Input file not found: {INPUT_FILE}"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Reading {INPUT_FILE}..."
            )
        )

        with open(
            INPUT_FILE,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as infile:

            reader = csv.DictReader(infile)

            fieldnames = reader.fieldnames or []

            # Add our new columns
            fieldnames += [
                "Latitude",
                "Longitude",
                "Geocoding Status",
            ]

            rows = list(reader)

        self.stdout.write(
            f"Found {len(rows)} stations."
        )

        # Load already processed stations if output exists
        processed = {}

        if os.path.exists(OUTPUT_FILE):

            self.stdout.write(
                "Existing output found. Resuming..."
            )

            with open(
                OUTPUT_FILE,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as outfile:

                existing_reader = csv.DictReader(outfile)

                for row in existing_reader:
                    station_id = row.get(
                        "OPIS Truckstop ID"
                    )

                    if station_id:
                        processed[station_id] = row

        output_rows = []

        for index, row in enumerate(rows, start=1):

            station_id = row["OPIS Truckstop ID"]

            # Skip already successfully processed stations
            if station_id in processed:

                existing = processed[station_id]

                if (
                    existing.get("Latitude")
                    and existing.get("Longitude")
                    and existing.get("Geocoding Status")
                    == "success"
                ):
                    output_rows.append(existing)

                    self.stdout.write(
                        f"[{index}/{len(rows)}] "
                        f"Skipping {station_id}"
                    )

                    continue

            address = row["Address"].strip()
            city = row["City"].strip()
            state = row["State"].strip()

            query = (
                f"{address}, "
                f"{city}, "
                f"{state}, USA"
            )

            self.stdout.write(
                f"[{index}/{len(rows)}] "
                f"Geocoding: {query}"
            )

            latitude = ""
            longitude = ""
            status = "failed"

            try:

                response = requests.get(
                    NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "us",
                    },
                    headers={
                        "User-Agent": USER_AGENT,
                    },
                    timeout=15,
                )

                response.raise_for_status()

                results = response.json()

                if results:

                    latitude = results[0]["lat"]
                    longitude = results[0]["lon"]
                    status = "success"

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ {latitude}, {longitude}"
                        )
                    )

                else:

                    status = "not_found"

                    self.stdout.write(
                        self.style.WARNING(
                            "  ! Location not found"
                        )
                    )

            except requests.RequestException as exc:

                status = "error"

                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Request failed: {exc}"
                    )
                )

            row["Latitude"] = latitude
            row["Longitude"] = longitude
            row["Geocoding Status"] = status

            output_rows.append(row)

            # Nominatim public service:
            # keep requests slow and respectful.
            time.sleep(1)

            # Save progress after every station
            self._save_rows(
                output_rows,
                fieldnames,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nGeocoding completed."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Output: {OUTPUT_FILE}"
            )
        )

    def _save_rows(self, rows, fieldnames):

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8",
            newline="",
        ) as outfile:

            writer = csv.DictWriter(
                outfile,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(rows)