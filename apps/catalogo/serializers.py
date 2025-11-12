from rest_framework import serializers
from .models import *
from apps.acceso_seguridad.models import Usuario

# --- (INICIO) SERIALIZADORES DE CLIENTE ---

class ClienteProfileSerializer(serializers.ModelSerializer):
    """ Serializador simple para los campos anidados de Cliente """
    class Meta:
        model = Cliente
        fields = ['ciudad', 'codigo_postal']

class ClienteReadSerializer(serializers.ModelSerializer):
    ciudad = serializers.CharField(source='cliente.ciudad', read_only=True, default='')
    codigo_postal = serializers.CharField(source='cliente.codigo_postal', read_only=True, default='')
    total_compras_calculado = serializers.SerializerMethodField()
    cliente_id = serializers.IntegerField(source='cliente.id', read_only=True)
    class Meta:
        model = Usuario 
        fields = [
            'id', 'cliente_id', 'correo', 'nombre', 'apellido', 'telefono', 
            'is_active', 'last_login', 'rol', 'ciudad', 
            'codigo_postal', 'total_compras_calculado'
        ]
        read_only_fields = fields 
    def get_total_compras_calculado(self, obj):
        return 0

class ClienteWriteSerializer(serializers.ModelSerializer):
    """
    Serializador de ESCRITURA (CRUD) para Clientes.
    Maneja el Usuario y el Perfil Cliente anidado.
    """
    # 1. Añadimos el perfil anidado (para que el formulario lo envíe)
    cliente = ClienteProfileSerializer()
    # 2. Añadimos el password (opcional)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        # 3. Incluimos TODOS los campos que el formulario envía
        fields = [
            'id', 'correo', 'password', 'nombre', 'apellido', 
            'telefono', 'is_active', 'rol', 'cliente' 
        ]
        # Hacemos 'password' opcional en 'update'
        extra_kwargs = {
            'password': {'required': False}
        }

    def to_internal_value(self, data):
        # Hacemos 'password' opcional en 'update'
        if self.instance and 'password' not in data:
            self.fields['password'].required = False
        # Hacemos 'password' obligatorio en 'create'
        if not self.instance and 'password' not in data:
                self.fields['password'].required = True
        return super().to_internal_value(data)

    def create(self, validated_data):
        # 1. Separamos los datos del perfil anidado
        cliente_data = validated_data.pop('cliente')
        
        # 2. Sacamos la contraseña
        password = validated_data.pop('password')
        
        # 3. Forzamos el rol a 'CLIENTE'
        validated_data['rol'] = 'CLIENTE'
        
        # 4. Creamos el Usuario
        try:
            usuario = Usuario(**validated_data)
            usuario.set_password(password)
            usuario.save()
        except Exception as e:
            raise serializers.ValidationError(str(e)) # Devuelve 400 si el correo ya existe
        
        # 5. Creamos el Perfil Cliente asociado
        Cliente.objects.create(usuario=usuario, **cliente_data)
        
        return usuario # Devolvemos el usuario

    def update(self, instance, validated_data):
        # 'instance' es el Usuario que se está actualizando
        
        # 1. Separamos los datos del perfil anidado (si vienen)
        cliente_data = validated_data.pop('cliente', None) # Usamos None como default
        
        # 2. Actualizamos el Usuario
        password = validated_data.pop('password', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save() # Guardamos el Usuario

        # 3. Actualizamos el Perfil Cliente (SIEMPRE)
        cliente_profile, created = Cliente.objects.get_or_create(usuario=instance)
        
        # Si el frontend envió datos de cliente, los actualizamos
        if cliente_data:
            cliente_profile.ciudad = cliente_data.get('ciudad', cliente_profile.ciudad)
            cliente_profile.codigo_postal = cliente_data.get('codigo_postal', cliente_profile.codigo_postal)
            cliente_profile.save()
        
        return instance



class CategoriaSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Categoria (CU-07).
    Añadido 'fecha_creacion' como solo lectura.
    """
    class Meta:
        model = Categoria
        fields = [
            "id", "nombre", "estado", 
            "fecha_creacion"
        ]
        read_only_fields = ["fecha_creacion"]
        
class ProductoSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Producto (CU-08).
    Añadidos campos faltantes del modelo y 'fecha_creacion' como solo lectura.
    Corregido 'año_garantia' a 'ano_garantia'.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            "id", "codigo_producto", "nombre", "descripcion", "precio_venta",
            "precio_compra", "imagen_url", "estado", "stock_actual", 
            "ano_garantia",
            "categoria", "categoria_nombre", "marca", "fecha_creacion"
        ]
        read_only_fields = ["fecha_creacion", "categoria_nombre"]

class InventarioProductoSerializer(serializers.ModelSerializer):
    """
    Serializador para el log de 'InventarioProducto' (CU-09).
    Añadido 'fecha_ingreso' como solo lectura.
    Mantiene tu lógica de 'producto' (lectura) y 'producto_id' (escritura).
    """
    producto = ProductoSerializer(read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(), source='producto', write_only=True
    )
    
    inventario_codigo = serializers.CharField(source='inventario.codigo', read_only=True)

    class Meta:
        model = InventarioProducto
        fields = [
            "id", "inventario", "inventario_codigo", "producto", "producto_id", 
            "cantidad", 
            "fecha_ingreso"
        ]
        read_only_fields = ["fecha_ingreso", "producto", "inventario_codigo"]

class InventarioSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Inventario (CU-09).
    Corregido 'nombre' por 'codigo' y añadidos campos 'estado' y 'fecha_creacion'.
    Tu lógica 'get_productos' se mantiene.
    """
    productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventario
        fields = [
            "id", 
            "codigo",
            "estado",
            "fecha_creacion",
            "productos"
        ]
        read_only_fields = ["fecha_creacion"]

    def get_productos(self, obj) -> list:
        # Devuelve el LOG de entradas de inventario para este almacén,
        # lo cual es correcto según el nuevo modelo 'InventarioProducto'.
        inventario_productos = InventarioProducto.objects.filter(inventario=obj)
        return InventarioProductoSerializer(inventario_productos, many=True).data