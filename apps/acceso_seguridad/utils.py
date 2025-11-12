import requests
from django.conf import settings
from firebase_admin import messaging
from .models import Device


def enviar_email_brevo(to_email, subject, html_content):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "sender": {
            "name": "SmartSales365", 
            "email": "yordangallardo21@gmail.com"
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 201:
        print(f"Error al enviar email a {to_email}: {r.status_code} - {r.text}")
    return r.json()

def enviar_notificacion(asunto, mensaje, urgente=False):
    """
    Envía notificación push a todos los dispositivos activos
    
    Args:
        asunto (str): Título de la notificación
        mensaje (str): Cuerpo del mensaje
        urgente (bool): Si es urgente, se envía con alta prioridad
    
    Returns:
        int: Número de notificaciones enviadas exitosamente
    """
    # Obtener todos los tokens activos
    tokens = list(Device.objects.filter(activo=True).values_list('token', flat=True))
    
    if not tokens:
        print("⚠️ No hay dispositivos registrados para enviar notificaciones")
        return 0

    print(f"📱 Enviando notificación a {len(tokens)} dispositivo(s)...")
    
    # Configurar el mensaje
    notification = messaging.Notification(
        title=asunto,
        body=mensaje,
    )
    
    # Configuración Android
    android_config = messaging.AndroidConfig(
        priority='high' if urgente else 'normal',
        notification=messaging.AndroidNotification(
            sound='default',
            color='#FF6B6B',  # Color del icono
        ),
    )
    
    # Enviar a cada dispositivo individualmente
    exitosos = 0
    fallidos = 0
    
    for token in tokens:
        try:
            # Crear mensaje individual
            message = messaging.Message(
                notification=notification,
                android=android_config,
                token=token,
            )
            
            # Enviar notificación
            response = messaging.send(message)
            exitosos += 1
            print(f"✅ Notificación enviada exitosamente: {response}")
            
        except Exception as e:
            fallidos += 1
            error_str = str(e)
            print(f"❌ Error al enviar a token {token[:20]}...: {error_str}")
            
            # Si el token es inválido, desactivarlo
            if 'not-found' in error_str.lower() or 'invalid' in error_str.lower() or 'unregistered' in error_str.lower():
                Device.objects.filter(token=token).update(activo=False)
                print(f"⚠️ Token inválido desactivado")
    
    print(f"📊 Resultado: {exitosos} exitosos, {fallidos} fallidos de {len(tokens)} total")
    return exitosos