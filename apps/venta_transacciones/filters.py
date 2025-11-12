
from django_filters import rest_framework as filters
from .models import Venta

class VentaFilter(filters.FilterSet):
    fecha_min = filters.DateFilter(field_name="fecha_venta__date", lookup_expr='gte')
    fecha_max = filters.DateFilter(field_name="fecha_venta__date", lookup_expr='lte')

    class Meta:
        model = Venta
        fields = [
            'cliente',
            'metodo_entrada',
            'tipo_venta',
        ]