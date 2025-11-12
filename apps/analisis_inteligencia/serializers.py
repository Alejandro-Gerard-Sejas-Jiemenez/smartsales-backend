from rest_framework import serializers
from .models import PrediccionVentas

class PrediccionVentasSerializer(serializers.ModelSerializer):
    """
    Serializador para leer los resultados de las predicciones de ventas (CU-16).
    """
    # Muestra el 'nombre' de la categoría en lugar de solo su ID
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = PrediccionVentas
        fields = [
            'id',
            'fecha_prediccion',
            'periodo_inicio',
            'periodo_fin',
            'venta_predicha',
            'confianza',
            'categoria', # ID de la categoría
            'categoria_nombre' # Nombre de la categoría
        ]