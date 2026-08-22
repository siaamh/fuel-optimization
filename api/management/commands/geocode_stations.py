import csv
import os
import time

import requests
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from django.core.management.base import BaseCommand


load_dotenv()


INPUT_FILE = (
    r"C:\Users\ASUS\Downloads"
    r"\fuel-prices-for-be-assessment - fuel-prices-for-be-assessment.csv"
)

OUTPUT_FILE = "fuel_stations_geocoded.csv"

GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/search"

API_KEY = os.getenv("GEOAPIFY_API_KEY")


class Command(BaseCommand):
    help = "Geocode unique fuel stations using Geoapify"

    def handle(self, *args, **options):

        # --------------------------------------------
        # Validate API key
        # --------------------------------------------

        if not API_KEY:
            self.stdout.write(
                self.style.ERROR(
                    "GEOAPIFY_API_KEY not found in .env"
                )
            )
            return

        # --------------------------------------------
        # Validate input CSV
        # --------------------------------------------

        if not os.path.exists(INPUT_FILE):
            self.stdout.write(
                self.style.ERROR(
                    f"Input CSV not found:\n{INPUT_FILE}"
                )
            )
            return

        # --------------------------------------------
        # Read CSV
        # --------------------------------------------

        rows = self.read_csv()

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(rows)} total price records."
            )
        )

        # --------------------------------------------
        # Extract unique stations
        # --------------------------------------------

        stations = {}

        for row in rows:

            station_id = row[
                "OPIS Truckstop ID"
            ].strip()

            if station_id not in stations:
                stations[station_id] = row

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(stations)} unique stations."
            )
        )

        # --------------------------------------------
        # Load previous successful results
        # --------------------------------------------

        processed = self.load_existing_results()

        self.stdout.write(
            f"Already geocoded: {len(processed)}"
        )

        # --------------------------------------------
        # Process stations
        # --------------------------------------------

        output_rows = list(processed.values())

        total = len(stations)

        for index, (station_id, row) in enumerate(
            stations.items(),
            start=1,
        ):

            # ----------------------------------------
            # Skip successfully processed station
            # ----------------------------------------

            if station_id in processed:

                self.stdout.write(
                    f"[{index}/{total}] "
                    f"Skipping {station_id}"
                )

                continue

            name = row[
                "Truckstop Name"
            ].strip()

            address = row[
                "Address"
            ].strip()

            city = row[
                "City"
            ].strip()

            state = row[
                "State"
            ].strip()

            self.stdout.write(
                f"\n[{index}/{total}] {name}"
            )

            self.stdout.write(
                f"  {city}, {state}"
            )

            # ----------------------------------------
            # Geocode
            # ----------------------------------------

            result = self.geocode_station(
                name=name,
                address=address,
                city=city,
                state=state,
            )

            # ----------------------------------------
            # Create output row
            # ----------------------------------------

            output_row = {
                "OPIS Truckstop ID": station_id,
                "Truckstop Name": name,
                "Address": address,
                "City": city,
                "State": state,
                "Rack ID": row["Rack ID"],
                "Retail Price": row["Retail Price"],
                "Latitude": result["latitude"],
                "Longitude": result["longitude"],
                "Geocoding Status": result["status"],
                "Geocoding Query": result["query"],
            }

            output_rows.append(output_row)

            # ----------------------------------------
            # Display result
            # ----------------------------------------

            if result["status"] == "success":

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ "
                        f"{result['latitude']}, "
                        f"{result['longitude']}"
                    )
                )

            else:

                self.stdout.write(
                    self.style.WARNING(
                        f"  ! {result['status']}"
                    )
                )

            # ----------------------------------------
            # Save immediately
            # ----------------------------------------

            self.save_results(output_rows)

            # ----------------------------------------
            # Small delay
            # ----------------------------------------

            time.sleep(0.2)

        # --------------------------------------------
        # Final save
        # --------------------------------------------

        self.save_results(output_rows)

        self.stdout.write(
            self.style.SUCCESS(
                "\n===================================="
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Geocoding completed!"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Output: {OUTPUT_FILE}"
            )
        )

    # ==================================================
    # READ CSV
    # ==================================================

    def read_csv(self):

        with open(
            INPUT_FILE,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            required_columns = [
                "OPIS Truckstop ID",
                "Truckstop Name",
                "Address",
                "City",
                "State",
                "Rack ID",
                "Retail Price",
            ]

            missing_columns = [
                column
                for column in required_columns
                if column not in reader.fieldnames
            ]

            if missing_columns:

                raise ValueError(
                    "Missing CSV columns: "
                    f"{missing_columns}"
                )

            return list(reader)

    # ==================================================
    # GEOCODE STATION
    # ==================================================

    def geocode_station(
        self,
        name,
        address,
        city,
        state,
    ):

        # --------------------------------------------
        # Query 1
        #
        # Most useful for truck stops.
        # --------------------------------------------

        queries = [
            (
                f"{name}, "
                f"{city}, "
                f"{state}, USA"
            ),

            # ----------------------------------------
            # Query 2
            # ----------------------------------------

            (
                f"{name}, "
                f"{address}, "
                f"{city}, "
                f"{state}, USA"
            ),

            # ----------------------------------------
            # Query 3
            # ----------------------------------------

            (
                f"{address}, "
                f"{city}, "
                f"{state}, USA"
            ),
        ]

        for query in queries:

            result = self.request_geocode(
                query
            )

            if result:

                return {
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    "status": "success",
                    "query": query,
                }

            # Small delay between fallback queries
            time.sleep(0.2)

        return {
            "latitude": "",
            "longitude": "",
            "status": "not_found",
            "query": queries[0],
        }

    # ==================================================
    # GEOAPIFY REQUEST
    # ==================================================

    def request_geocode(self, query):

        try:

            response = requests.get(
                GEOAPIFY_URL,
                params={
                    "text": query,
                    "apiKey": API_KEY,
                    "limit": 1,
                },
                headers={
                    "Accept": "application/json",
                },
                timeout=15,
            )

            response.raise_for_status()

            data = response.json()

        except requests.RequestException as exc:

            self.stdout.write(
                self.style.ERROR(
                    f"  API request failed: {exc}"
                )
            )

            return None

        # --------------------------------------------
        # Geoapify returns GeoJSON
        # --------------------------------------------

        features = data.get(
            "features",
            []
        )

        if not features:
            return None

        feature = features[0]

        properties = feature.get(
            "properties",
            {}
        )

        # Geoapify also provides lon/lat in properties
        latitude = properties.get("lat")
        longitude = properties.get("lon")

        # --------------------------------------------
        # Fallback to geometry
        # --------------------------------------------

        if latitude is None or longitude is None:

            geometry = feature.get(
                "geometry",
                {}
            )

            coordinates = geometry.get(
                "coordinates",
                []
            )

            if len(coordinates) >= 2:

                longitude = coordinates[0]
                latitude = coordinates[1]

        if latitude is None or longitude is None:
            return None

        return {
            "latitude": latitude,
            "longitude": longitude,
        }

    # ==================================================
    # LOAD EXISTING SUCCESSFUL RESULTS
    # ==================================================

    def load_existing_results(self):

        processed = {}

        if not os.path.exists(
            OUTPUT_FILE
        ):
            return processed

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                station_id = row.get(
                    "OPIS Truckstop ID"
                )

                if not station_id:
                    continue

                # Only skip stations that actually
                # have coordinates.

                if (
                    row.get("Latitude")
                    and row.get("Longitude")
                    and row.get(
                        "Geocoding Status"
                    ) == "success"
                ):

                    processed[
                        station_id
                    ] = row

        return processed

    # ==================================================
    # SAVE RESULTS
    # ==================================================

    def save_results(self, rows):

        fieldnames = [
            "OPIS Truckstop ID",
            "Truckstop Name",
            "Address",
            "City",
            "State",
            "Rack ID",
            "Retail Price",
            "Latitude",
            "Longitude",
            "Geocoding Status",
            "Geocoding Query",
        ]

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8",
            newline="",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            writer.writerows(rows)