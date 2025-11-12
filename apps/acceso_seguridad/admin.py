from django.contrib import admin
from .models import Usuario, Device, Aviso

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'correo', 'nombre', 'is_active')
    search_fields = ('correo', 'nombre')

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plataforma', 'activo', 'fecha_registro')
    list_filter = ('activo', 'plataforma')
    search_fields = ('user__correo', 'token')
    readonly_fields = ('fecha_registro',)

@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ('id', 'asunto', 'estado', 'fecha_push')
    list_filter = ('estado',)
    search_fields = ('asunto', 'mensaje')
    readonly_fields = ('fecha_push',)
