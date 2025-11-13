import traceback
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import PrediccionVentas
from .serializers import PrediccionVentasSerializer
from django_filters.rest_framework import DjangoFilterBackend

from .utils_reports import generate_dynamic_report
from django.http import HttpResponse    
from apps.venta_transacciones.models import Venta


class PrediccionVentasViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite ver las predicciones de ventas (CU-16).
    """
    queryset = PrediccionVentas.objects.all().order_by('-periodo_inicio')
    serializer_class = PrediccionVentasSerializer
    permission_classes = [permissions.IsAuthenticated] # O IsAdminRole
    
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['categoria']


class ReportesViewSet(viewsets.ViewSet):
    """
    API endpoint para la Generación Dinámica de Reportes (CU-12).
    """
    permission_classes = [permissions.IsAuthenticated] # O IsAdminRole

    @action(detail=False, methods=['post'], url_path='generar_reporte')
    def generar_reporte(self, request):
        prompt = request.data.get('prompt', '')
        if not prompt:
            return Response({'error': 'El prompt de texto es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            return generate_dynamic_report(prompt)

        # Capturamos el error específico que lanzamos si no hay datos
        except Venta.DoesNotExist as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print("❌ ERROR EN REPORTE DINÁMICO:")
            traceback.print_exc()   # 👈 esto imprimirá la causa real
            return Response({'error': f'Error al procesar el reporte: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)