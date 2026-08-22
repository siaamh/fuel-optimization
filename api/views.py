from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import RouteRequestSerializer
from api.services.routing import RoutingService
from api.services.stations import StationService
from api.services.optimizer import OptimizationService


class OptimizeRouteView(APIView):
    """
    POST /api/optimize/

    Body:
        { "start": "New York, NY", "finish": "Los Angeles, CA" }

    Returns the driving route, optimal fuel stops, and total fuel cost.
    """

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start = serializer.validated_data["start"]
        finish = serializer.validated_data["finish"]

        
        # 1. Get driving route (ORS)
       
        routing = RoutingService()
        route = routing.get_route(start, finish)

        if not route:
            return Response(
                {"error": "Could not compute a route for the given locations. "
                          "Check that both locations are valid US addresses."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        
        # 2. Find fuel stations near the route (haversine filter)
        
        station_service = StationService()
        stations = station_service.get_stations_near_route(
            route_geometry=route["geometry"],
            route_distance_miles=route["distance_miles"],
        )

        
        # 3. Optimize fueling stops
        
        optimization = OptimizationService()
        result = optimization.optimize(
            stations=stations,
            route_distance=route["distance_miles"],
            initial_fuel=OptimizationService.TANK_CAPACITY,  # start with a full tank
        )

        
        # 4. Return combined response
        
        return Response({
            # "route": {
            #     "start": start,
            #     "finish": finish,
            #     "distance_miles": route["distance_miles"],
            #     "duration_minutes": route["duration_minutes"],
            #     "geometry": route["geometry"],
            # },
            "fuel_stops": result["stops"],
            "total_fuel_cost": result["total_cost"],
            "stations_checked": len(stations),
        })