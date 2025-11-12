from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrediccionVentasViewSet

router = DefaultRouter()
router.register('predicciones', PrediccionVentasViewSet, basename='predicciones')

urlpatterns = [
    path('', include(router.urls)),
]