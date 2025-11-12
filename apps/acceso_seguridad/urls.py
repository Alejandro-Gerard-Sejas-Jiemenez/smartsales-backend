from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView
from .views import registrar_token


router = DefaultRouter()
router.register('usuarios', UsuarioViewSet, basename='usuarios')
router.register('bitacora', BitacoraViewSet, basename='bitacora')
router.register('avisos', AvisoViewSet, basename='avisos')

urlpatterns = [
    path('acceso_seguridad/token/', LoginJWTView.as_view(), name='token_obtain_pair'),
    path('acceso_seguridad/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('acceso_seguridad/logout/', LogoutJWTView.as_view(), name='logout'),
    path('acceso_seguridad/perfil/', PerfilView.as_view(), name='perfil'),
    path('acceso_seguridad/registro/', RegistroView.as_view(), name='registro'),
    path('acceso_seguridad/solicitar-recuperacion/', SolicitarRecuperacionView.as_view(), name='solicitar_recuperacion'),
    path('acceso_seguridad/confirmar-recuperacion/', ConfirmarRecuperacionView.as_view(), name='confirmar_recuperacion'),
    path('acceso_seguridad/', include(router.urls)),
    path('acceso_seguridad/registrar-token/', registrar_token),
]
