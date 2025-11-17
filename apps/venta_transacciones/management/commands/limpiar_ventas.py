from django.core.management.base import BaseCommand
from django.db import transaction

# Importamos todos los modelos que vamos a limpiar
from apps.venta_transacciones.models import Venta, DetalleVenta, Pago, Carrito, DetalleCarrito
from apps.analisis_inteligencia.models import PrediccionVentas
from apps.catalogo.models import InventarioProducto

class Command(BaseCommand):
    help = 'Limpia todas las tablas transaccionales (Ventas, Carritos, Predicciones) en el orden correcto.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('--- INICIANDO LIMPIEZA DE DATOS (Modo Seguro) ---'))

        # NO usamos SQL en bruto. Borramos usando el ORM en el orden de dependencia.
        
        self.stdout.write(self.style.NOTICE('Borrando Predicciones de IA...'))
        PrediccionVentas.objects.all().delete()
        
        self.stdout.write(self.style.NOTICE('Borrando Pagos...'))
        Pago.objects.all().delete()
        
        self.stdout.write(self.style.NOTICE('Borrando Detalles de Ventas...'))
        DetalleVenta.objects.all().delete()
        
        self.stdout.write(self.style.NOTICE('Borrando Detalles de Carritos...'))
        DetalleCarrito.objects.all().delete()

        self.stdout.write(self.style.NOTICE('Borrando Ventas...'))
        Venta.objects.all().delete()
        
        self.stdout.write(self.style.NOTICE('Borrando Carritos...'))
        Carrito.objects.all().delete()

        self.stdout.write(self.style.NOTICE('Borrando Historial de Ingresos de Stock...'))
        InventarioProducto.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('--- LIMPIEZA COMPLETADA ---'))