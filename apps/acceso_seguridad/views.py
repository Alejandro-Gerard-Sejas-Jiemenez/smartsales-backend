from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .utils import enviar_email_brevo,enviar_notificacion
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import random
import string
import secrets
from .models import Device  # lo crearás en models.py
from rest_framework.decorators import api_view,permission_classes



from .models import Usuario, Bitacora, Aviso
from .serializers import (
    UsuarioReadSerializer,
    UsuarioWriteSerializer,
    RegistroSerializer,
    PerfilSerializer,
    CambiarPasswordSerializer,
    BitacoraSerializer,
    SolicitarRecuperacionSerializer,
    ConfirmarRecuperacionSerializer,
    RecuperarPasswordSerializer,
    AvisoSerializer
)


# LOGIN usando correo + password => devuelve access / refresh y usuario
class LoginJWTView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        print("🟢 === LOGINJWTVIEW INICIADA ===")
        print("🟢 Request data:", request.data)
        
        correo = request.data.get("correo")
        password = request.data.get("password")
        
        print(f"🟢 Credenciales: {correo} / {password}")

        # Verificar si existe el usuario
        try:
            print("🟢 Buscando usuario en BD...")
            usuario = Usuario.objects.get(correo=correo)
            print(f"🟢 Usuario encontrado: {usuario.correo}")

            # Verificar si está bloqueado
            if usuario.esta_bloqueado():
                print("🔴 Usuario bloqueado")
                tiempo_restante = (
                    usuario.bloqueado_hasta - timezone.now()
                ).seconds // 60
                return Response(
                    {
                        "detail": "Usuario bloqueado por múltiples intentos fallidos",
                        "bloqueado": True,
                        "minutos_restantes": tiempo_restante,
                    },
                    status=status.HTTP_423_LOCKED,
                )

        except Usuario.DoesNotExist:
            print("🔴 Usuario no existe en BD")
            return Response(
                {"detail": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception as e:
            print(f"🔴 Error inesperado: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"detail": "Error interno del servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Autenticar
        print("🟢 Intentando autenticar...")
        user = authenticate(request, correo=correo, password=password)
        
        if not user:
            print("🔴 Autenticación fallida")
            # Incrementar intentos fallidos
            usuario.incrementar_intentos_fallidos()
            registrar_bitacora(
                usuario,
                "LOGIN_FALLIDO",
                f'Intento de login fallido desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                request,
            )

            if usuario.intentos_fallidos >= 3:
                return Response(
                    {
                        "detail": "Usuario bloqueado por múltiples intentos fallidos. Solicita recuperación de contraseña.",
                        "bloqueado": True,
                        "debe_recuperar": True,
                    },
                    status=status.HTTP_423_LOCKED,
                )

            return Response(
                {
                    "detail": "Credenciales inválidas",
                    "intentos_restantes": 3 - usuario.intentos_fallidos,
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        else:
            print("🟢 Autenticación exitosa")

        if not user.is_active:
            print("🔴 Usuario inactivo")
            return Response(
                {"detail": "Usuario inactivo"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Login exitoso - resetear intentos fallidos
        user.resetear_intentos_fallidos()
        registrar_bitacora(
            user,
            "LOGIN",
            f'Login exitoso desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
            request,
        )

        refresh = RefreshToken.for_user(user)
        print("🟢 Token generado exitosamente")
        
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "usuario": UsuarioReadSerializer(user).data,
            }
        )

# PERFIL (requiere Bearer token)
class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = PerfilSerializer(request.user)
        user = request.user
        registrar_bitacora(
            user,
            "PERFIL",
            f'Acceso a perfil desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
            request,
        )
        return Response(ser.data)

# USUARIOS CRUD
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = (
        Usuario.objects.all()
        .order_by("id")
    )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UsuarioWriteSerializer
        return UsuarioReadSerializer

    @action(detail=True, methods=["post"])
    def cambiar_password(self, request, pk=None):
        usuario = self.get_object()
        serializer = CambiarPasswordSerializer(data=request.data)

        if serializer.is_valid():
            # Verificar password actual
            if not usuario.check_password(serializer.validated_data["password_actual"]):
                return Response({"detail": "Contraseña actual incorrecta"}, status=400)

            # Cambiar password
            usuario.set_password(serializer.validated_data["password_nueva"])
            usuario.save()
            return Response({"detail": "Contraseña actualizada correctamente"})

        return Response(serializer.errors, status=400)


class LogoutJWTView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Falta refresh"}, status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # requiere app blacklist
        except Exception:
            return Response({"detail": "Refresh inválido"}, status=400)
        return Response({"detail": "OK"})


class RegistroView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegistroSerializer

    def post(self, request):
        ser = RegistroSerializer(data=request.data)
        if ser.is_valid():
            user = ser.save()
            registrar_bitacora(
                user,
                "REGISTRO",
                f'Registro exitoso desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                request,
            )
            return Response(
                {"id": user.id, "correo": user.correo}, status=status.HTTP_201_CREATED
            )
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


# Recuperar contraseña - Simple sin email
class RecuperarPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RecuperarPasswordSerializer(data=request.data)
        if serializer.is_valid():
            correo = serializer.validated_data["correo"]
            try:
                usuario = Usuario.objects.get(correo=correo, is_active=True)

                # Generar password temporal simple
                temp_password = "".join(
                    random.choices(string.ascii_letters + string.digits, k=8)
                )
                usuario.set_password(temp_password)
                usuario.save()
                registrar_bitacora(
                    usuario,
                    "RECUPERAR_PASSWORD",
                    f'Contraseña recuperada desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                    request,
                )
                return Response(
                    {
                        "detail": "Password temporal generada",
                        "temp_password": temp_password,
                    }
                )

            except Usuario.DoesNotExist:
                return Response(
                    {"detail": "Si el correo existe, se enviará la nueva contraseña"}
                )

        return Response(serializer.errors, status=400)

# Solicitar recuperación de contraseña - Envía email con token
class SolicitarRecuperacionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SolicitarRecuperacionSerializer(data=request.data)
        if serializer.is_valid():
            correo = serializer.validated_data["correo"]
            try:
                usuario = Usuario.objects.get(correo=correo, is_active=True)

                # Generar token seguro
                token = secrets.token_urlsafe(32)
                usuario.token_recuperacion = token
                usuario.token_expira = timezone.now() + timezone.timedelta(hours=1)
                usuario.save()

                # Enviar email con Brevo
                try:
                    enviar_email_brevo(
                        to_email=correo,
                        subject="Recuperación de Contraseña - SmartSales365",
                        html_content=f"""
                        <p>Hola {usuario.nombre},</p>
                        <p>Has solicitado recuperar tu contraseña. Usa el siguiente token para crear una nueva contraseña:</p>
                        <p><b>{token}</b></p>
                        <p>Este token expira en 1 hora.</p>
                        <p>Si no solicitaste este cambio, ignora este email.</p>
                        <br>
                        <p>Saludos,<br>Equipo SmartSales365</p>
                        """,
                    )

                    registrar_bitacora(
                        usuario,
                        "SOLICITAR_RECUPERACION",
                        f'Token de recuperación enviado desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                        request,
                    )

                    return Response(
                        {
                            "detail": "Se ha enviado un token de recuperación a tu email",
                            "email_enviado": True,
                        }
                    )

                except Exception as e:
                    return Response(
                        {
                            "detail": "Error al enviar email con Brevo",
                            "error": str(e),
                            "token_temporal": token,  # Solo para desarrollo
                        }
                    )

            except Usuario.DoesNotExist:
                pass

        return Response(
            {"detail": "Si el correo existe, se enviará el token de recuperación"}
        )


# Confirmar recuperación con token
class ConfirmarRecuperacionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConfirmarRecuperacionSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data["token"]
            nueva_password = serializer.validated_data["nueva_password"]

            try:
                usuario = Usuario.objects.get(
                    token_recuperacion=token,
                    token_expira__gt=timezone.now(),
                    is_active=True,
                )

                # Cambiar contraseña
                usuario.set_password(nueva_password)
                usuario.token_recuperacion = None
                usuario.token_expira = None
                # Desbloquear usuario y resetear intentos
                usuario.resetear_intentos_fallidos()
                usuario.save()

                registrar_bitacora(
                    usuario,
                    "RECUPERACION_EXITOSA",
                    f'Contraseña recuperada exitosamente desde {request.META.get("REMOTE_ADDR", "IP desconocida")}',
                    request,
                )

                return Response(
                    {"detail": "Contraseña actualizada correctamente", "exito": True}
                )

            except Usuario.DoesNotExist:
                return Response(
                    {"detail": "Token inválido o expirado"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bitacora.objects.all().select_related("usuario").order_by("-fecha")
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated]


# Función helper para registrar en bitácora
def registrar_bitacora(usuario, accion, descripcion="", request=None):
    ip = None
    if request:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
    Bitacora.objects.create(
        usuario=usuario, accion=accion, descripcion=descripcion, ip=ip
    )

class AvisoViewSet(viewsets.ModelViewSet):
    queryset = Aviso.objects.all().order_by('-fecha_push')
    serializer_class = AvisoSerializer
    
    def perform_create(self, serializer):
        """
        Al crear un aviso:
        - Si modo_envio='inmediato' → Envía notificación AHORA
        - Si modo_envio='programado' → Guarda con estado 'Programado' (se enviará después)
        """
        aviso = serializer.save()
        modo_envio = self.request.data.get('modo_envio', 'inmediato')
        
        print(f"\n📤 ==========================================")
        print(f"📤 NUEVO AVISO CREADO: {aviso.asunto}")
        print(f"📤 Modo de envío: {modo_envio}")
        print(f"📤 ==========================================\n")
        
        if modo_envio == 'inmediato':
            # Enviar inmediatamente
            print(f"⚡ Enviando notificación INMEDIATA...")
            try:
                enviados = enviar_notificacion(
                    asunto=aviso.asunto,
                    mensaje=aviso.mensaje,
                    urgente=(aviso.tipo == 'Urgente')
                )
                
                if enviados > 0:
                    aviso.estado = 'Enviado'
                    print(f"✅ Notificación enviada a {enviados} dispositivo(s)")
                else:
                    aviso.estado = 'FALLIDO'
                    print(f"⚠️ No hay dispositivos registrados")
                    
            except Exception as e:
                aviso.estado = 'FALLIDO'
                print(f"❌ Error al enviar: {str(e)}")
                
            aviso.save()
            
        else:  # programado
            # Solo guardar, se enviará después
            aviso.estado = 'Programado'
            aviso.save()
            print(f"📅 Aviso programado para: {aviso.fecha_push} {aviso.hora_push}")
    
    @action(detail=True, methods=['post'], url_path='enviar')
    def enviar_aviso(self, request, pk=None):
        """
        Endpoint para enviar notificación push manualmente
        POST /api/acceso_seguridad/avisos/{id}/enviar/
        Requiere: Usuario autenticado con rol ADMIN
        """
        print(f"\n🔔 ============================================")
        print(f"🔔 ENDPOINT ENVIAR AVISO LLAMADO - ID: {pk}")
        print(f"🔔 Usuario: {request.user}")
        print(f"🔔 Rol: {request.user.rol if hasattr(request.user, 'rol') else 'N/A'}")
        print(f"🔔 Es superusuario: {request.user.is_superuser}")
        print(f"🔔 ============================================\n")
        
        # Validar que solo ADMIN o superusuario pueda enviar
        if not (request.user.is_superuser or request.user.rol == 'ADMIN'):
            print(f"❌ Permiso denegado - Rol: {request.user.rol}, Superuser: {request.user.is_superuser}")
            return Response(
                {'error': 'No tienes permisos para enviar notificaciones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        aviso = self.get_object()
        print(f"📄 Aviso encontrado: {aviso.asunto}")
        
        try:
            print(f"🚀 Iniciando envío de notificación...")
            # Enviar notificación a todos los dispositivos
            enviados = enviar_notificacion(
                asunto=aviso.asunto,
                mensaje=aviso.mensaje,
                urgente=(aviso.asunto.lower().find('urgente') >= 0)
            )
            
            print(f"📊 Dispositivos alcanzados: {enviados}")
            
            if enviados > 0:
                aviso.estado = 'ENVIADO'
                aviso.save()
                print(f"✅ Aviso marcado como ENVIADO")
                return Response({
                    'mensaje': f'Notificación enviada a {enviados} dispositivos',
                    'exitosos': enviados,
                    'estado': 'ENVIADO'
                })
            else:
                print(f"⚠️ No hay dispositivos registrados")
                return Response(
                    {'error': 'No hay dispositivos registrados para enviar notificaciones'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            print(f"❌❌❌ EXCEPCIÓN CAPTURADA: {type(e).__name__}")
            print(f"❌ Mensaje de error: {str(e)}")
            import traceback
            print(f"❌ Traceback completo:")
            traceback.print_exc()
            
            aviso.estado = 'FALLIDO'
            aviso.save()
            return Response(
                {'error': f'Error al enviar notificación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )  


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def registrar_token(request):
    token = request.data.get('token')
    plataforma = request.data.get('plataforma', 'android')
    if not token:
        return Response({'detail': 'Token requerido'}, status=400)
    Device.objects.update_or_create(
        token=token,
        defaults={'user': request.user, 'plataforma': plataforma, 'activo': True}
    )
    return Response({'ok': True})
