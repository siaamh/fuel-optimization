# services/station_service.py

class StationService:

    ROUTE_BUFFER_MILES = 5

    def get_stations_near_route(self, route_geometry):
        """
        Find fuel stations within 5 miles
        of the actual driving route.
        """

        # PostGIS query

        return stations