import math
import os

from api.models import FuelStation


# ---------------------------------------------------------------------------
# Haversine helpers (pure Python — no PostGIS required)
# ---------------------------------------------------------------------------

def _haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles between two (lat, lon) points."""
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _point_to_segment_distance_miles(px, py, ax, ay, bx, by):
    """
    Minimum distance in miles from point P=(px,py) to line segment A-B.
    Also returns t ∈ [0,1] — the parameter of the closest point on the segment.
    Coordinates are (longitude, latitude).
    """
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return _haversine_miles(py, px, ay, ax), 0.0

    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx = ax + t * dx
    cy = ay + t * dy
    return _haversine_miles(py, px, cy, cx), t


class StationService:

    def get_stations_near_route(self, route_geometry, route_distance_miles):
        """
        Returns a list of station dicts sorted by distance_from_start (miles).

        route_geometry — GeoJSON LineString geometry dict from ORS
            { "type": "LineString", "coordinates": [[lon, lat], ...] }
        route_distance_miles — total route length in miles (from ORS summary)
        """
        buffer_miles = float(os.getenv("ROUTE_BUFFER_MILES", "5"))

        # Decode the route polyline into (lon, lat) pairs
        coords = route_geometry["coordinates"]  # [[lon, lat], ...]

        # Build segment cumulative-distance lookup so we can compute
        # distance_from_start for each matched station.
        seg_start_miles = []
        cumulative = 0.0
        for i in range(len(coords) - 1):
            seg_start_miles.append(cumulative)
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            cumulative += _haversine_miles(lat1, lon1, lat2, lon2)
        seg_start_miles.append(cumulative)  # sentinel for last vertex

        total_seg_length = cumulative  # sanity check matches route_distance_miles

        # Fetch all stations from DB (SQLite/MySQL friendly — no spatial ops)
        all_stations = FuelStation.objects.all().values(
            'id', 'opis_id', 'name', 'retail_price', 'latitude', 'longitude'
        )

        nearby = []

        for station in all_stations:
            lat, lon = station['latitude'], station['longitude']
            if lat is None or lon is None:
                continue

            best_dist = float('inf')
            best_dist_from_start = 0.0

            # Check each segment of the route polyline
            for i in range(len(coords) - 1):
                ax, ay = coords[i]      # lon, lat
                bx, by = coords[i + 1]  # lon, lat

                dist, t = _point_to_segment_distance_miles(
                    lon, lat, ax, ay, bx, by
                )

                if dist < best_dist:
                    best_dist = dist
                    # Miles from route start to the closest point on this segment
                    seg_len = _haversine_miles(ay, ax, by, bx)
                    best_dist_from_start = seg_start_miles[i] + t * seg_len

            if best_dist <= buffer_miles:
                nearby.append({
                    'id': station['id'],
                    'name': station['name'],
                    'price': float(station['retail_price']),
                    'distance_from_start': round(best_dist_from_start, 2),
                    'latitude': lat,
                    'longitude': lon,
                })

        # Sort by distance along the route
        nearby.sort(key=lambda s: s['distance_from_start'])
        return nearby