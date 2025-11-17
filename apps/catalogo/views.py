from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction  # <--- IMPORTACIÓN AÑADIDA
from apps.acceso_seguridad.models import Usuario
from apps.acceso_seguridad.permissions import IsAdminRole, IsAdminOrReadOnly
from .models import *
from .serializers import (
    ClienteReadSerializer, 
    ClienteWriteSerializer, 
    CategoriaSerializer, 
    ProductoSerializer, 
    InventarioSerializer,
    InventarioProductoSerializer
)

# === VIEWSET DE CLIENTE) ===
class ClienteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    queryset = Usuario.objects.filter(rol='CLIENTE', cliente__isnull=False).select_related('cliente').order_by('nombre')
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'apellido', 'correo', 'cliente__ciudad']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClienteWriteSerializer
        return ClienteReadSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer) 
        
        serializer.instance.refresh_from_db()

        read_serializer = ClienteReadSerializer(serializer.instance)
        
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        serializer.instance.refresh_from_db()

        read_serializer = ClienteReadSerializer(instance)
        
        return Response(read_serializer.data)


    @action(detail=True, methods=['post'], url_path='toggle-estado')
    def toggle_estado(self, request, pk=None):
        try:
            usuario = self.get_object() 
            if usuario.rol != 'CLIENTE':
                return Response({"detail": "Este usuario no es un cliente."}, status=status.HTTP_400_BAD_REQUEST)
            
            usuario.is_active = not usuario.is_active
            usuario.save()
            
            serializer = ClienteReadSerializer(usuario) 
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"detail": f"Error al cambiar el estado: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

# --- Categoria (CU-07) ---
class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all().order_by('id')
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdminOrReadOnly]  # ✅ CLIENTES pueden ver, ADMIN pueden editar
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre']

# --- Producto (CU-08) ---
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.select_related('categoria').all().order_by('id') # Optimizado con select_related
    serializer_class = ProductoSerializer
    permission_classes = [IsAdminOrReadOnly]  # ✅ CLIENTES pueden ver, ADMIN pueden editar
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_producto', 'categoria__nombre', 'marca'] # Añadido 'marca'

# --- Inventario (CU-09) ---
class InventarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar los 'Almacenes' (Inventarios).
    """
    queryset = Inventario.objects.all().order_by('id')
    serializer_class = InventarioSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [filters.SearchFilter]
    search_fields = ['codigo']

# --- InventarioProducto (CU-09) ---
class InventarioProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para 'Registrar Ingresos' de productos al inventario (CU-09).
    Maneja la lógica de actualizar el stock_actual del producto.
    """
    queryset = InventarioProducto.objects.select_related('producto', 'inventario').all().order_by('-fecha_ingreso')
    serializer_class = InventarioProductoSerializer
    permission_classes = [IsAdminRole]
    
    # Solo permitimos listar, ver detalle y CREAR. No permitimos modificar/borrar.
    http_method_names = ['get', 'post', 'head', 'options']

    def create(self, request, *args, **kwargs):
        """
        Sobrescribe el método 'create' para actualizar el stock del producto
        de forma atómica (todo o nada).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Usamos una transacción para asegurar la integridad de los datos
        try:
            with transaction.atomic():
                # 1. Obtenemos los datos validados ANTES de guardar
                producto = serializer.validated_data['producto']
                cantidad_ingresada = serializer.validated_data['cantidad']
                
                # 2. Guardamos el registro de ingreso (InventarioProducto)
                self.perform_create(serializer)
                
                # 3. Actualizamos el stock_actual del Producto
                # (Usamos 'select_for_update' para bloquear la fila y evitar 'race conditions')
                producto_a_actualizar = Producto.objects.select_for_update().get(pk=producto.id)
                producto_a_actualizar.stock_actual += cantidad_ingresada
                producto_a_actualizar.save()

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except Exception as e:
            return Response(
                {"detail": f"Error en la transacción: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # --- Métodos deshabilitados para proteger la integridad del stock ---

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "No permitido. No se pueden modificar registros de ingreso."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        return Response(
            {"detail": "No permitido. No se pueden modificar registros de ingreso."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No permitido. No se pueden eliminar registros de ingreso."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

