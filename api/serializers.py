from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(
        help_text="Starting US location, e.g. 'New York, NY'"
    )
    finish = serializers.CharField(
        help_text="Destination US location, e.g. 'Los Angeles, CA'"
    )