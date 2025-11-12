from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.acceso_seguridad.models import Usuario
from .models import Cliente


@receiver(post_save, sender=Usuario)
def crear_perfil_cliente(sender, instance, created, **kwargs):
    """
    Crea automáticamente un perfil de Cliente cuando se crea un Usuario con rol CLIENTE.
    
    Esta señal se ejecuta después de guardar un Usuario y:
    - Solo actúa si es un usuario nuevo (created=True)
    - Solo crea el Cliente si el rol es 'CLIENTE'
    - Evita duplicados verificando si ya existe
    """
    if created and instance.rol == 'CLIENTE':
        # Verificar si ya existe un perfil de cliente (por seguridad)
        if not hasattr(instance, 'cliente'):
            Cliente.objects.create(usuario=instance)
            print(f"✓ Perfil de Cliente creado automáticamente para: {instance.correo}")
