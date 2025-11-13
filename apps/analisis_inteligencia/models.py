from django.db import models
from apps.catalogo.models import Categoria 
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class PrediccionVentas(models.Model):
    """
    Este modelo almacena los resultados de las predicciones de ventas (CU-16)
    basado en el script SQL del proyecto.
    """
    id = models.AutoField(primary_key=True) 
    
    # La fecha en que se corrió la predicción
    fecha_prediccion = models.DateTimeField(default=timezone.now)
    
    # El rango de fechas para el cual es esta predicción
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    
    # El resultado
    venta_predicha = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Nivel de confianza (ej. 95.50%)
    confianza = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))]
    )
    
    # La predicción está vinculada a una Categoría específica
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-fecha_prediccion', 'categoria', 'periodo_inicio']
        verbose_name = "Predicción de Venta"
        verbose_name_plural = "Predicciones de Ventas"

    def __str__(self):
        return f"Predicción para {self.categoria.nombre} ({self.periodo_inicio} a {self.periodo_fin})"
