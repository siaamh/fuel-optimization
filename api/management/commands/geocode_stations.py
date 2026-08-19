import csv
import os
import time
import requests
from django.core.management.base import BaseCommand
from api.services.routing import RoutingService

NOMATIM_URL = "https://nominatim.openstreetmap.org/search"
ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search/structured"
USER_AGENT = "fuel-optimization/1.0"


class Command(BaseCommand):
    help = "Geocode fuel station CSV with multi-strategy fallback"

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            default="fuel_stations_geocoded.csv",
            help="Input CSV path",
        )
        parser.add_argument(
            "--output",
            default="fuel_stations_geocoded.csv",
            help="Output CSV path",
        )

    def handle(self, *args, **options):
        input_file = options["input"]
        output_file = options["output"]

        if not os.path.exists(input_file):
            self.stdout.write(self.style.ERROR(f"File not found: {input_file}"))
            return

        routing = RoutingService()

        with open(input_file, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            for col in ["Latitude", "Longitude", "Geocoding Status"]:
                if col not in fieldnames:
                    fieldnames.append(col)
            rows = list(reader)

        self.stdout.write(f"Found {len(rows)} stations.")

        processed = self._load_existing(output_file)

        output_rows = []

        for i, row in enumerate(rows, 1):
            sid = row["OPIS Truckstop ID"]

            if sid in processed and processed[sid].get("Geocoding Status") == "success":
                output_rows.append(processed[sid])
                self.stdout.write(f"[{i}/{len(rows)}] Skipping {sid}")
                continue

            address = row["Address"].strip()
            city = row["City"].strip()
            state = row["State"].strip()

            self.stdout.write(f"[{i}/{len(rows)}] {row['Truckstop Name']} — {city}, {state}")

            lat, lon, status = self._geocode_with_fallback(
                routing, address, city, state
            )

            row["Latitude"] = lat
            row["Longitude"] = lon
            row["Geocoding Status"] = status
            output_rows.append(row)

            if status == "success":
                self.stdout.write(self.style.SUCCESS(f"  -> {lat}, {lon}"))
            else:
                self.stdout.write(self.style.WARNING(f"  -> {status}"))

            time.sleep(1.1)

            self._save(output_rows, fieldnames, output_file)

        self.stdout.write(self.style.SUCCESS(f"\nDone. Output: {output_file}"))

    def _geocode_with_fallback(self, routing, address, city, state):
        """Try multiple query strategies in order of specificity."""

        queries = [
            f"{address}, {city}, {state}, USA",
            f"{city}, {state}, USA",
            f"{address}, {state}, USA",
        ]

        for query in queries:
            lat, lon = self._try_nominatim(query)
            if lat:
                return lat, lon, "success_nominatim"

        ors_result = self._try_ors(routing, address, city, state)
        if ors_result:
            lat, lon = ors_result
            return lat, lon, "success_ors"

        return "", "", "not_found"

    def _try_nominatim(self, query):
        try:
            resp = requests.get(
                NOMATIM_URL,
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except requests.RequestException:
            pass
        return None, None

    def _try_ors(self, routing, address, city, state):
        """Use ORS structured geocoding as last resort."""
        if not routing.ors_api_key:
            return None

        try:
            resp = requests.get(
                ORS_GEOCODE_URL,
                params={
                    "api_key": routing.ors_api_key,
                    "address": address,
                    "locality": city,
                    "region": state,
                    "country": "US",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                return coords[1], coords[0]  # ORS returns [lon, lat]
        except requests.RequestException:
            pass

        return None

    def _load_existing(self, path):
        processed = {}
        if not os.path.exists(path):
            return processed
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                sid = row.get("OPIS Truckstop ID")
                if sid:
                    processed[sid] = row
        return processed

    def _save(self, rows, fieldnames, path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
