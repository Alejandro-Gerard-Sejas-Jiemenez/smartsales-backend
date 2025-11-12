from rest_framework import viewsets, permissions
from .models import PrediccionVentas
from .serializers import PrediccionVentasSerializer
from django_filters.rest_framework import DjangoFilterBackend

class PrediccionVentasViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite ver las predicciones de ventas (CU-16).
    """
    queryset = PrediccionVentas.objects.all().order_by('-periodo_inicio')
    serializer_class = PrediccionVentasSerializer
    permission_classes = [permissions.IsAuthenticated] # O IsAdminRole
    
    # Permite filtrar por categoría (ej: /api/predicciones/?categoria=3)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['categoria']
    
