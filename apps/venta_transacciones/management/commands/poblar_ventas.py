import random
from datetime import timedelta, datetime # <-- Importamos datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from tqdm import tqdm 

from apps.catalogo.models import Producto, Cliente
from apps.venta_transacciones.models import Venta, DetalleVenta

# --- CONFIGURACIÓN DE LA SIMULACIÓN ---
TOTAL_VENTAS_A_CREAR = 1500
# Usamos un objeto datetime, pero lo tratamos como fecha
FECHA_FINAL_BASE = timezone.datetime(2025, 11, 10) 
DIAS_HISTORIAL = 360 # 1 año de historial

PROB_FIN_DE_SEMANA = 0.7 
MAX_PRODUCTOS_POR_VENTA = 5

class Command(BaseCommand):
    help = 'Genera 1500 ventas históricas realistas para entrenar la IA.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE(f'--- Iniciando simulación de {TOTAL_VENTAS_A_CREAR} ventas... ---'))
        
        clientes = list(Cliente.objects.filter(usuario__is_active=True))
        productos = list(Producto.objects.filter(estado='Disponible'))
        
        if not clientes or not productos:
            self.stdout.write(self.style.ERROR('Error: No hay suficientes Clientes o Productos en la BD para generar ventas.'))
            return

        self.stdout.write(f'Usando {len(clientes)} clientes y {len(productos)} productos como base.')
        
        ventas_creadas = []
        detalles_creados = []
        
        for _ in tqdm(range(TOTAL_VENTAS_A_CREAR)):
            
            cliente_random = random.choice(clientes)
            fecha_venta = self.get_fecha_aleatoria()
            
            venta = Venta(
                cliente=cliente_random,
                fecha_venta=fecha_venta,
                metodo_entrada=random.choice(['Móvil', 'Mostrador']),
                tipo_venta=Venta.TipoVenta.CONTADO,
                total=0 
            )
            ventas_creadas.append(venta)
            
            num_productos = random.randint(1, MAX_PRODUCTOS_POR_VENTA)
            total_venta_calculado = 0
            
            for _ in range(num_productos):
                producto_random = random.choice(productos)
                cantidad_comprada = random.randint(1, 3)
                subtotal = producto_random.precio_venta * cantidad_comprada
                
                detalles_creados.append(
                    DetalleVenta(
                        venta=venta, 
                        producto=producto_random,
                        cantidad=cantidad_comprada,
                        precio_unitario=producto_random.precio_venta,
                        subtotal=subtotal,
                        fecha_creacion=fecha_venta
                    )
                )
                total_venta_calculado += subtotal
            
            venta.total = total_venta_calculado
        
        self.stdout.write(self.style.NOTICE('\nGuardando ventas en la base de datos...'))
        Venta.objects.bulk_create(ventas_creadas)
        
        self.stdout.write(self.style.NOTICE('Guardando detalles de venta...'))
        for i, detalle in enumerate(detalles_creados):
            detalle.venta_id = detalle.venta.id
            
        DetalleVenta.objects.bulk_create(detalles_creados)

        self.stdout.write(self.style.SUCCESS(f'--- Simulación completada: {TOTAL_VENTAS_A_CREAR} ventas creadas ---'))

    def get_fecha_aleatoria(self):
        """
        Devuelve una fecha aleatoria en el último año,
        priorizando fines de semana (Sábado=5, Domingo=6).
        """
        dia_aleatorio = random.randint(0, DIAS_HISTORIAL - 1)
        fecha = (FECHA_FINAL_BASE - timedelta(days=dia_aleatorio)).date() # Obtenemos solo la parte de la fecha
        
        if random.random() < PROB_FIN_DE_SEMANA:
            while fecha.weekday() < 4: 
                fecha = fecha + timedelta(days=1)
        
        hora = random.randint(9, 21)
        minuto = random.randint(0, 59)
        
        # 1. Convertir la 'date' (fecha) de nuevo a 'datetime'
        dt = datetime.combine(fecha, datetime.min.time())
        
        # 2. Ahora sí podemos usar .replace() con la hora, minuto y zona horaria
        return dt.replace(hour=hora, minute=minuto, tzinfo=timezone.get_current_timezone())