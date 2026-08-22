from django.contrib import admin
from django.urls import path, include

from api.views import OptimizeRouteView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/optimize/', OptimizeRouteView.as_view(), name='optimize-route'),
]
