from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *


router = DefaultRouter()
router.register(r'pagos', PagoViewSet, basename='pagos')
router.register(r'ventas', VentaViewSet, basename='ventas')
router.register(r'detalles-venta', DetalleVentaViewSet, basename='detalles-venta')
router.register(r'carritos', CarritoViewSet, basename='carritos')
router.register(r'detalles-carrito', DetalleCarritoViewSet, basename='detalles-carrito')

urlpatterns = [
    path('', include(router.urls)),
]

