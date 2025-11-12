from apps.acceso_seguridad.models import Usuario
from django.db import models
from decimal import Decimal
from django.utils import timezone
from django.core.validators import MinValueValidator

# --- Modelo Cliente ---
class Cliente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='cliente')
    ciudad = models.CharField(max_length=120, blank=True, null=True)
    codigo_postal = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.usuario.correo

# --- Modelo Categoria (CU-07) ---
class Categoria(models.Model):
    nombre = models.CharField(max_length=150, unique=True) # unique=True como en el script SQL
    estado = models.BooleanField(default=True)
    
    # CAMPO AÑADIDO: Requerido por el script SQL
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        
    def __str__(self):
        return self.nombre

# --- Modelo Producto (CU-08) ---
class Producto(models.Model):
    
    # CORRECCIÓN: El script SQL requiere 3 estados, no un Boolean 
    class EstadoProducto(models.TextChoices):
        DISPONIBLE = 'Disponible', 'Disponible'
        AGOTADO = 'Agotado', 'Agotado'
        DESCONTINUADO = 'Descontinuado', 'Descontinuado'

    codigo_producto = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    
    # CORRECCIÓN: Añadido validador para cumplir con el CHECK >= 0 del SQL
    precio_venta = models.DecimalField(
        max_digits=10, decimal_places=2, 
        default=0.00, validators=[MinValueValidator(Decimal('0.00'))]
    )
    precio_compra = models.DecimalField(
        max_digits=10, decimal_places=2, 
        default=0.00, validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    imagen_url = models.URLField(max_length=500, blank=True, null=True) # El script usa 500 [cite: 940]
    
    #CORREGIDO: De Boolean a CharField
    estado = models.CharField(
        max_length=20, 
        choices=EstadoProducto.choices, 
        default=EstadoProducto.DISPONIBLE
    )
    
    stock_actual = models.PositiveIntegerField(default=0)
    ano_garantia = models.PositiveIntegerField(default=0) # Mantenemos tu campo
    
    # CORRECCIÓN: El script SQL usa RESTRICT para evitar borrar categorías con productos 
    categoria = models.ForeignKey(Categoria, on_delete=models.RESTRICT, related_name='productos')

    # CAMPOS AÑADIDOS: Requeridos por el script SQL
    marca = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f"{self.nombre} - {self.codigo_producto}"

# --- Modelo Inventario (CU-09) ---
# CORRECCIÓN: Modelo alineado al script SQL (usa 'codigo' en lugar de 'nombre')
class Inventario(models.Model):
    # --- CAMBIO AQUÍ ---
    # Añadimos 'null=True' y 'blank=True'
    codigo = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    productos = models.ManyToManyField(Producto, through='InventarioProducto', related_name='inventarios')

    class Meta:
        ordering = ['id']
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'

    def __str__(self):
        # Si el código es null, muestra el ID para evitar errores
        return self.codigo or f"Inventario #{self.id}"

# --- Modelo InventarioProducto (CU-09) ---
# El CU-09 "Registrar Ingreso"  implica registrar múltiples ingresos del mismo producto.
class InventarioProducto(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=0) # [cite: 957]
    fecha_ingreso = models.DateTimeField(default=timezone.now) # [cite: 958]

    class Meta:
        # CORRECCIÓN: Se eliminó 'unique_together'
        verbose_name = 'Entrada de Inventario'
        verbose_name_plural = 'Entradas de Inventario'
        ordering = ['-fecha_ingreso']

    def __str__(self):
        return f"Ingreso: {self.producto.nombre} (+{self.cantidad}) en {self.inventario.codigo} el {self.fecha_ingreso.strftime('%Y-%m-%d')}"

