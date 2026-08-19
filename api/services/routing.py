# services/routing.py
import os
import requests


class RoutingService:

    def __init__(self, ors_api_key: str | None = None):
        """Initializes the routing service with an OpenRouteService API key.

        If not provided explicitly, it attempts to load from the ORS_API_KEY
        environment variable.
        """
        self.ors_api_key = ors_api_key or os.getenv("ORS_API_KEY")

    def geocode(self, location: str) -> tuple[float, float] | None:
        """Geocodes a location string into (latitude, longitude) using Nominatim."""
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "MyTestApp/1.0 (write2siam.h@gmail.com)"}
        params = {"q": location, "format": "json", "limit": 1}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except requests.RequestException as e:
            print(f"Geocoding network error for '{location}': {e}")
        except (KeyError, IndexError, ValueError) as e:
            print(f"Geocoding parsing error for '{location}': {e}")

        return None

    # Alias to keep backward compatibility if get_geocode was called elsewhere
    get_geocode = geocode

    def get_route(self, start: str, finish: str) -> dict | None:
        """Returns driving distance, duration, and route geometry using OpenRouteService."""
        if not self.ors_api_key:
            print(
                "Error: OpenRouteService API key is missing. "
                "Pass it to RoutingService(ors_api_key=...) or set the ORS_API_KEY environment variable."
            )
            return None

        start_coords = self.geocode(start)  # Returns (lat, lon)
        finish_coords = self.geocode(finish)  # Returns (lat, lon)

        if not start_coords or not finish_coords:
            print("Failed to geocode one or both locations.")
            return None

        # Unpack lat/lon and swap to (lon, lat) required by OpenRouteService
        start_lat, start_lon = start_coords
        finish_lat, finish_lon = finish_coords

        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        params = {
            "api_key": self.ors_api_key,
            "start": f"{start_lon},{start_lat}",
            "end": f"{finish_lon},{finish_lat}",
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract summary properties and geometry from GeoJSON response
            properties = data["features"][0]["properties"]["summary"]
            geometry = data["features"][0]["geometry"]

            # Convert meters -> miles and seconds -> minutes
            distance_miles = round(properties["distance"] / 1609.34, 2)
            duration_minutes = round(properties["duration"] / 60, 1)

            return {
                "distance_miles": distance_miles,
                "duration_minutes": duration_minutes,
                "geometry": geometry,
            }
        except requests.RequestException as e:
            print(f"Routing HTTP error: {e}")
        except (KeyError, IndexError) as e:
            print(f"Routing response parsing error: {e}")

        return None

# ------------------------------------------------------------------
# Test directly from terminal by running: python services/routing.py
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== TESTING ROUTING SERVICE ===")

    # Pass your API key directly here, or leave empty if ORS_API_KEY is in your environment
    service = RoutingService(ors_api_key="eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjYwYzZhNzc2NzNmNzQ4NWRhODNiM2FhZmM5M2I1MWRkIiwiaCI6Im11cm11cjY0In0=")

    # 1. Test Geocoding directly
    service.geocode("Berlin, Germany")

    # 2. Test Full Route Calculation
    result = service.get_route("Berlin", "Munich")
    print("\nReturned Dict:", result)