from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from .filters import VentaFilter
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import stripe

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError # Usamos la de DRF
from rest_framework import viewsets, permissions, status, filters

from .models import *
from .serializers import *
from apps.catalogo.models import Producto
from django.db.models.functions import TruncMonth
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

# ViewSet para Venta
class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.select_related('cliente__usuario').prefetch_related('detalles__producto').all().order_by('-fecha_venta')
    permission_classes = [permissions.IsAuthenticated] 

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = VentaFilter
    search_fields = ['cliente__usuario__nombre', 'cliente__usuario__apellido', 'cliente__usuario__correo']
    ordering_fields = ['fecha_venta', 'total']

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve' or self.action == 'mis_compras':
            return VentaReadSerializer
        return VentaSerializer

    @action(detail=True, methods=['get'], url_path='comprobante')
    def generar_comprobante(self, request, pk=None):
        """
        Genera una Nota de Venta (Comprobante) en PDF para una venta específica (CU-14).
        """
        try:
            # 1. Obtener los datos de la Venta
            venta = self.get_object() # Obtiene la venta por su PK (ej. /api/ventas/23/...)
            cliente = venta.cliente.usuario
            detalles = venta.detalles.all()

            # 2. Configurar la respuesta HTTP como un PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="nota_venta_{venta.id}.pdf"'

            # 3. Crear el PDF con ReportLab
            p = canvas.Canvas(response, pagesize=letter)
            width, height = letter # (8.5 x 11 pulgadas)
            
            p.setFont("Helvetica-Bold", 16)
            p.drawString(1 * inch, height - 1 * inch, "SmartSales365 - NOTA DE VENTA")

            p.setFont("Helvetica", 12)
            p.drawString(1 * inch, height - 1.5 * inch, f"Venta ID: {venta.id}")
            p.drawString(1 * inch, height - 1.7 * inch, f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}")
            
            p.setFont("Helvetica-Bold", 12)
            p.drawString(1 * inch, height - 2.2 * inch, "Cliente:")
            p.setFont("Helvetica", 12)
            p.drawString(1 * inch, height - 2.4 * inch, f"Nombre: {cliente.nombre} {cliente.apellido}")
            p.drawString(1 * inch, height - 2.6 * inch, f"Correo: {cliente.correo}")

            # --- Encabezados de la tabla de detalles ---
            p.setFont("Helvetica-Bold", 11)
            p.drawString(1 * inch, height - 3.2 * inch, "Producto")
            p.drawString(4 * inch, height - 3.2 * inch, "Cantidad")
            p.drawString(5 * inch, height - 3.2 * inch, "P. Unitario")
            p.drawString(6 * inch, height - 3.2 * inch, "Subtotal")
            p.line(1 * inch, height - 3.3 * inch, width - 1 * inch, height - 3.3 * inch)

            # --- Loop de Detalles ---
            p.setFont("Helvetica", 10)
            y = height - 3.6 * inch # Posición Y inicial
            for item in detalles:
                p.drawString(1 * inch, y, item.producto.nombre)
                p.drawString(4.2 * inch, y, str(item.cantidad))
                p.drawString(5.2 * inch, y, f"{item.precio_unitario:.2f} Bs")
                p.drawString(6.2 * inch, y, f"{item.subtotal:.2f} Bs")
                y -= 0.3 * inch # Moverse a la siguiente línea

            # --- Total ---
            p.line(1 * inch, y + 0.1 * inch, width - 1 * inch, y + 0.1 * inch)
            p.setFont("Helvetica-Bold", 14)
            p.drawString(5 * inch, y - 0.3 * inch, f"TOTAL: {venta.total:.2f} Bs")

            # 4. Finalizar y enviar el PDF
            p.showPage()
            p.save()
            return response

        except Exception as e:
            return Response({'error': f'Error al generar PDF: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='analisis-tendencias')
    def analisis_tendencias(self, request):
        """
        Devuelve el historial de ventas (Monto y Cantidad)
        agrupado por mes durante los últimos 12 meses.
        """
        try:
            # 1. Definir el rango de fechas (últimos 12 meses)
            hace_un_ano = timezone.now() - timedelta(days=365)

            # 2. Consultar usando el ORM de Django
            tendencias = Venta.objects.filter(fecha_venta__gte=hace_un_ano) \
                                    .annotate(mes=TruncMonth('fecha_venta')) \
                                    .values('mes') \
                                    .annotate(
                                        cantidad_ventas=Count('id'), 
                                        monto_total=Sum('total')
                                    ) \
                                    .order_by('mes')

            # 3. Formatear la salida
            # Convertimos 'mes' (datetime) a un string "YYYY-MM"
            data_formateada = [
                {
                    "mes": item['mes'].strftime('%Y-%m'),
                    "cantidad_ventas": item['cantidad_ventas'],
                    "monto_total": item['monto_total']
                }
                for item in tendencias
            ]

            return Response(data_formateada, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Error al generar tendencias: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # NOTE: top-productos endpoint removed per user request (reverted changes)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        
        detalles_data = request.data.pop('detalles', [])
        if not detalles_data:
            return Response({"error": "La venta debe tener al menos un producto."}, status=status.HTTP_400_BAD_REQUEST)

        total_calculado = 0
        productos_a_actualizar = []
        detalles_a_crear = []

        try:
            for item in detalles_data:
                producto = Producto.objects.select_for_update().get(id=item['producto_id'])
                cantidad_pedida = int(item['cantidad'])

                if cantidad_pedida <= 0:
                    raise ValidationError(f"La cantidad para {producto.nombre} debe ser mayor a 0.")
                
                if producto.stock_actual < cantidad_pedida:
                    raise ValidationError(f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.stock_actual}, Pedido: {cantidad_pedida}")

                producto.stock_actual -= cantidad_pedida
                productos_a_actualizar.append(producto)

                subtotal = producto.precio_venta * cantidad_pedida
                total_calculado += subtotal
                
                detalles_a_crear.append(
                    DetalleVenta(
                        producto=producto, 
                        cantidad=cantidad_pedida, 
                        precio_unitario=producto.precio_venta, 
                        subtotal=subtotal
                    )
                )

            venta_serializer = VentaSerializer(data=request.data)
            venta_serializer.is_valid(raise_exception=True)
            # Guardamos la venta con el total calculado
            venta = venta_serializer.save(total=total_calculado)

            for detalle in detalles_a_crear:
                detalle.venta = venta
            
            DetalleVenta.objects.bulk_create(detalles_a_crear)
            
            Producto.objects.bulk_update(productos_a_actualizar, ['stock_actual'])

            read_serializer = VentaReadSerializer(venta)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)

        except Producto.DoesNotExist:
            return Response({"error": "Uno de los productos no existe."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error inesperado: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def mis_compras(self, request):
        """Obtiene el historial de compras del cliente autenticado"""
        user = request.user
        
        if not hasattr(user, 'cliente'):
            return Response(
                {'detail': 'El usuario no tiene un perfil de cliente asociado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener ventas del cliente con sus detalles
        ventas = Venta.objects.filter(
            cliente=user.cliente
        ).select_related(
            'cliente__usuario'
        ).prefetch_related(
            'detalles__producto'
        ).order_by('-fecha_venta')
        
        print(f"🔍 Ventas encontradas: {ventas.count()}")
        for venta in ventas:
            print(f"📦 Venta {venta.id}: {venta.detalles.count()} detalles")
        
        # Serializar las ventas
        serializer = self.get_serializer(ventas, many=True)
        print(f"📋 Datos serializados: {serializer.data}")
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- ViewSet para DetalleVenta (Solo Lectura) ---
class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    # --- Tomado de 'Incoming' (versión mía) ---
    queryset = DetalleVenta.objects.all().order_by('id')
    serializer_class = DetalleVentaSerializer
    permission_classes = [permissions.IsAuthenticated]

# ViewSet para Carrito
class CarritoViewSet(viewsets.ModelViewSet):
    # --- FUSIONADO: Tomado de 'HEAD' (Alejandro) pero MODIFICADO ---
    serializer_class = CarritoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar carritos del usuario autenticado (si es cliente)
        user = self.request.user
        if hasattr(user, 'cliente'):
            # Optimizar con select_related y prefetch_related
            # CORREGIDO: 'detalles' es el related_name correcto
            return Carrito.objects.filter(cliente=user.cliente).select_related(
                'cliente', 'cliente__usuario'
            ).prefetch_related(
                'detalles__producto'
            ).order_by('id')
        return Carrito.objects.none()
    
    @action(detail=False, methods=['post'])
    def vaciar_carrito(self, request):
        """Elimina todos los productos del carrito del usuario"""
        user = request.user
        
        if not hasattr(user, 'cliente'):
            return Response(
                {'detail': 'El usuario no tiene un perfil de cliente asociado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener el carrito del cliente
        carrito = Carrito.objects.filter(cliente=user.cliente).first()
        
        if not carrito:
            return Response(
                {'detail': 'No hay carrito para vaciar'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Eliminar todos los detalles del carrito
        DetalleCarrito.objects.filter(carrito=carrito).delete()
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'
        
        return Response(
            {'detail': 'Carrito vaciado exitosamente'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def crear_venta_desde_carrito(self, request):
        """Crea una venta a partir del carrito actual del usuario"""
        user = request.user

        if not hasattr(user, 'cliente'):
            return Response(
                {'detail': 'El usuario no tiene un perfil de cliente asociado.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener el carrito del cliente
        carrito = Carrito.objects.filter(cliente=user.cliente).first()
        
        if not carrito:
            return Response({"detail": "No hay carrito disponible"}, status=status.HTTP_404_NOT_FOUND)
        
        # Verificar que el carrito tenga productos
        detalles_carrito = DetalleCarrito.objects.filter(carrito=carrito)
        
        if not detalles_carrito.exists():
            return Response({"detail": "El carrito está vacío"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calcular el total desde los detalles del carrito
        total_calculado = sum(detalle.subtotal for detalle in detalles_carrito)
        
        # Crear la venta
        venta = Venta.objects.create(
            cliente=user.cliente,
            total=total_calculado,
            metodo_entrada='carrito',
            tipo_venta='online'
        )
        
        # Crear los detalles de la venta desde el carrito
        for detalle_carrito in detalles_carrito:
            DetalleVenta.objects.create(
                venta=venta,
                producto=detalle_carrito.producto,
                cantidad=detalle_carrito.cantidad,
                precio_unitario=detalle_carrito.precio_unitario,
                subtotal=detalle_carrito.subtotal
            )
        
        # Recargar la venta con sus detalles y productos relacionados
        venta = Venta.objects.prefetch_related('detalles__producto').get(id=venta.id)
        
        # Vaciar el carrito después de crear la venta
        detalles_carrito.delete()
        carrito.estado = 'Convertido'
        carrito.save()
        
        # Serializar la venta con VentaReadSerializer para incluir todos los detalles
        serializer = VentaReadSerializer(venta)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def create(self, request, *args, **kwargs):
        user = request.user

        if not hasattr(user, 'cliente'):
            raise ValidationError({'detail': 'El usuario no tiene un perfil de cliente asociado.'})

        # Verificar si ya existe un carrito
        carrito_existente = Carrito.objects.filter(cliente=user.cliente).first()
        if carrito_existente:
            # Si ya existe, devolvemos ese carrito como JSON (no error)
            serializer = self.get_serializer(carrito_existente)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Si no existe, creamos uno nuevo
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cliente=user.cliente)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# ViewSet para DetalleCarrito
class DetalleCarritoViewSet(viewsets.ModelViewSet):
    # --- FUSIONADO: Tomado de 'HEAD' (compañero) pero MODIFICADO ---
    serializer_class = DetalleCarritoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar detalles de carritos del usuario autenticado
        user = self.request.user
        if hasattr(user, 'cliente'):
            # CORREGIDO: 'carrito__cliente'
            return DetalleCarrito.objects.filter(carrito__cliente=user.cliente).order_by('id')
        return DetalleCarrito.objects.none()
    
    def perform_create(self, serializer):
        # Obtener o crear carrito del cliente autenticado
        user = self.request.user
        
        # Verificar que el usuario tenga un cliente asociado
        if not hasattr(user, 'cliente'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'El usuario no tiene un perfil de cliente asociado.'})
        
        # Obtener o crear el carrito activo
        carrito, created = Carrito.objects.get_or_create(
            cliente=user.cliente,
            estado='Activo',
            defaults={'origen': 'FlutterApp'}
        )
        
        # Obtener el producto y calcular precios
        from apps.catalogo.models import Producto
        producto_id = self.request.data.get('producto')
        cantidad = int(self.request.data.get('cantidad', 1))
        
        producto = Producto.objects.get(id=producto_id)
        
        # Verificar si el producto ya existe en el carrito
        detalle_existente = DetalleCarrito.objects.filter(
            carrito=carrito,
            producto=producto
        ).first()
        
        if detalle_existente:
            # Si ya existe, incrementar la cantidad
            detalle_existente.cantidad += cantidad
            
            # Validar stock total en carrito
            if producto.stock_actual < detalle_existente.cantidad:
                raise ValidationError({'detail': f'Stock insuficiente. Ya tiene {detalle_existente.cantidad - cantidad} en el carrito. Disponible: {producto.stock_actual}'})

            detalle_existente.subtotal = detalle_existente.precio_unitario * detalle_existente.cantidad
            detalle_existente.save()
            
            # CORREGIDO: Eliminada la lógica de 'carrito.total'
            
            # Retornar - no continuar con el save del serializer
            return
        
        # Si no existe, crear uno nuevo
        precio_unitario = producto.precio_venta
        subtotal = precio_unitario * cantidad
        
        # Guardar el detalle del carrito
        serializer.save(
            carrito=carrito,
            precio_unitario=precio_unitario,
            subtotal=subtotal
        )
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'
    
    def partial_update(self, request, *args, **kwargs):
        """Actualizar la cantidad de un detalle del carrito"""
        detalle = self.get_object()
        nueva_cantidad = request.data.get('cantidad')
        
        if nueva_cantidad is None:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'La cantidad es requerida'})
        
        nueva_cantidad = int(nueva_cantidad)
        
        if nueva_cantidad <= 0:
            # Si la cantidad es 0 o negativa, eliminar el detalle
            detalle.delete()
            
            # CORREGIDO: Eliminada la lógica de 'carrito.total'
            
            return Response({'detail': 'Producto eliminado del carrito'}, status=status.HTTP_204_NO_CONTENT)
        
        # Actualizar cantidad y subtotal
        detalle.cantidad = nueva_cantidad
        detalle.subtotal = detalle.precio_unitario * nueva_cantidad
        detalle.save()
        
        # CORREGIDO: Eliminada la lógica de 'carrito.total'
        
        serializer = self.get_serializer(detalle)
        return Response(serializer.data)




# Configurar Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PagoCreateSerializer
        return PagoSerializer

    @action(detail=False, methods=['post'])
    def crear_payment_intent(self, request):
        """
        Crear un PaymentIntent de Stripe vinculado a una venta.
        Espera 'venta_id' en el body.
        """
        try:
            venta_id = request.data.get('venta_id')
            if not venta_id:
                return Response({'error': 'venta_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
            
            venta = Venta.objects.get(id=venta_id)
            monto_centavos = int(float(venta.total_venta) * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=monto_centavos,
                currency='usd',
                metadata={'venta_id': venta.id}
            )
            
            pago = Pago.objects.create(
                venta=venta,
                monto=venta.total_venta,
                metodo_pago='stripe',
                estado='pendiente',
                stripe_payment_intent_id=intent.id,
                stripe_client_secret=intent.client_secret
            )
            
            return Response({
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'pago_id': pago.id,
                'monto': float(venta.total_venta),
                'venta_id': venta.id
            })
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def confirmar_pago(self, request):
        """Confirmar el pago después de que Stripe lo procese exitosamente"""
        try:
            payment_intent_id = request.data.get('payment_intent_id')
            if not payment_intent_id:
                return Response({'error': 'payment_intent_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

            # Verificar el estado del pago en Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status != 'succeeded':
                return Response({
                    'error': 'El pago no ha sido completado',
                    'status': intent.status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Buscar el pago en la base de datos
            pago = Pago.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
            
            if not pago:
                return Response({'error': 'Pago no encontrado'}, status=status.HTTP_404_NOT_FOUND)
            
            # Actualizar el estado del pago
            pago.estado = 'completado'
            pago.save()
            
            # Vaciar el carrito del cliente
            venta = pago.venta
            if hasattr(venta, 'cliente'):
                carrito = Carrito.objects.filter(cliente=venta.cliente).first()
                if carrito:
                    DetalleCarrito.objects.filter(carrito=carrito).delete()
                    carrito.total = 0
                    carrito.save()

            return Response({
                'message': 'Pago confirmado exitosamente',
                'pago_id': pago.id,
                'venta_id': venta.id,
                'estado': 'completado'
            })
        except Venta.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
