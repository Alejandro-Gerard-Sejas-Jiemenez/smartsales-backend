
from rest_framework import serializers
from .models import *

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_imagen = serializers.CharField(source='producto.imagen_url', read_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = [
            'id', 'venta', 'producto', 'producto_nombre', 'producto_imagen', 
            'cantidad', 'precio_unitario', 'subtotal'
        ]

class VentaReadSerializer(serializers.ModelSerializer):
    """Serializador para LECTURA de ventas con todos los detalles"""
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    total_venta = serializers.DecimalField(source='total', max_digits=10, decimal_places=2, read_only=True)
    metodo_pago = serializers.CharField(source='metodo_entrada', read_only=True)
    
    # Campos adicionales que el frontend espera pero que no están en el modelo
    estado = serializers.SerializerMethodField()
    descuento = serializers.SerializerMethodField()
    notas = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = [
            'id', 'cliente', 'fecha_venta', 'total', 'total_venta', 'metodo_entrada', 
            'metodo_pago', 'tipo_venta', 'estado', 'descuento', 'notas', 'detalles'
        ]
        read_only_fields = ['fecha_venta']
    
    def get_estado(self, obj):
        """Devuelve 'Completada' por defecto para ventas existentes"""
        return 'Completada'
    
    def get_descuento(self, obj):
        """Devuelve 0 como descuento por defecto"""
        return 0.0
    
    def get_notas(self, obj):
        """Devuelve None o string vacío para notas"""
        return None

# --- Serializador de Venta (Escritura) ---
class VentaSerializer(serializers.ModelSerializer):
    # --- (Sin Conflicto) ---
    class Meta:
        model = Venta
        fields = [
            'id', 
            'cliente', 
            'fecha_venta', 
            'metodo_entrada', 
            'tipo_venta', 
            'total', 
        ]
        read_only_fields = ['total', 'fecha_venta']


# --- Serializadores de Carrito ---
class DetalleCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_imagen = serializers.CharField(source='producto.imagen_url', read_only=True)
    producto_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = DetalleCarrito
        fields = [
            'id', 'carrito', 'producto', 'producto_nombre', 'producto_imagen', 
            'producto_info', 'cantidad', 'precio_unitario', 'subtotal'
        ]
        read_only_fields = ['carrito', 'precio_unitario', 'subtotal']  # Se calculan automáticamente
    
    def get_producto_info(self, obj):
        """Devuelve información completa del producto"""
        from apps.catalogo.serializers import ProductoSerializer
        return ProductoSerializer(obj.producto).data

class CarritoSerializer(serializers.ModelSerializer):
    detalles = DetalleCarritoSerializer(many=True, read_only=True)  # CORREGIDO: sin source, usa el related_name 'detalles'
    cliente_nombre = serializers.CharField(source='cliente.usuario.nombre', read_only=True)
    cliente_correo = serializers.CharField(source='cliente.usuario.correo', read_only=True)
    
    class Meta:
        model = Carrito
        fields = [
            'id', 'cliente', 'cliente_nombre', 'cliente_correo', 'fecha_creacion', 'estado', 'origen', 'detalles'
        ]
        read_only_fields = ['cliente', 'fecha_creacion', 'estado', 'origen']  # El cliente se asigna automáticamente

class PagoSerializer(serializers.ModelSerializer):
    venta = VentaSerializer(read_only=True)
    venta_id = serializers.PrimaryKeyRelatedField(queryset=Venta.objects.all(), source='venta', write_only=True)
    
    class Meta:
        model = Pago
        fields = [
            'id', 'venta', 'venta_id', 'monto', 'metodo_pago', 'estado',
            'stripe_payment_intent_id', 'stripe_client_secret',
            'fecha_creacion', 'fecha_actualizacion', 'referencia_pago', 'notas'
        ]
        read_only_fields = ['stripe_payment_intent_id', 'stripe_client_secret']

class PagoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ['venta', 'monto', 'metodo_pago']