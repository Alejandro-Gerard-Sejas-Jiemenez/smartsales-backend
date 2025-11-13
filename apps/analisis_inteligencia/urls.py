from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrediccionVentasViewSet, ReportesViewSet

router = DefaultRouter()
router.register('predicciones', PrediccionVentasViewSet, basename='predicciones')
router.register('reportes', ReportesViewSet, basename='reportes')

urlpatterns = [
    path('', include(router.urls)),
]