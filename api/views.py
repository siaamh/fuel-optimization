
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import RouteRequestSerializer


# Create your views here.
class OptimizeRouteView(APIView):

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = optimize_route(
            start=serializer.validated_data["start"],
            finish=serializer.validated_data["finish"],
        )

        return Response(result)