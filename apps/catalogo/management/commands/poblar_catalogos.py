import random
from faker import Faker
from django.core.management.base import BaseCommand
from django.db import transaction
from tqdm import tqdm 
import unicodedata
import re

from apps.acceso_seguridad.models import Usuario
from apps.catalogo.models import Categoria, Producto, Cliente

# --- CONFIGURACIÓN DE LA SIMULACIÓN ---
CLIENTES_A_CREAR = 100
PRODUCTOS_A_CREAR = 200

NOMBRES_PRODUCTOS = [
    "Refrigerador No-Frost 300L", "Lavadora Carga Frontal 12kg", "Cocina 6 Hornillas Inox",
    "Horno Eléctrico 45L", "Microondas Digital 20L", "Licuadora 5 Vel.", "Batidora de Pedestal",
    "Aspiradora Ciclónica", "Smart TV LED 55in 4K", "Barra de Sonido 2.1", "Cafetera Express",
    "Extractor de Jugos", "Plancha a Vapor Cerámica", "Ventilador de Torre", "Calefactor Eléctrico",
    "Aspiradora Robot R2", "Freidora de Aire 5L", "Hervidor de Agua 1.7L", "TV LED 42in Full HD",
    "Secadora de Ropa 10kg", "Congelador Horizontal 200L"
]
MARCAS = ["TechNova", "Elecson", "HogarPro", "FrioMax", "LavaTech", "StarView", "SonicFlow"]

def slugify_email_name(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[\s_-]+', '.', text)
    text = re.sub(r'[^a-z0-9.]', '', text)
    return text

class Command(BaseCommand):
    help = f'Genera clientes y productos falsos hasta alcanzar el total deseado.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('--- Iniciando poblamiento de catálogos... ---'))
        
        fake = Faker('es_ES')
        
        # --- 1. CREAR CLIENTES---
        clientes_existentes = Cliente.objects.count()
        clientes_a_crear_ahora = CLIENTES_A_CREAR - clientes_existentes
        
        if clientes_a_crear_ahora <= 0:
            self.stdout.write(self.style.SUCCESS(f'Ya existen {clientes_existentes} clientes. No se crearán nuevos.'))
        else:
            self.stdout.write(f'Creando {clientes_a_crear_ahora} clientes realistas nuevos...')
            usuarios_creados = []
            clientes_creados = []
            
            for i in tqdm(range(clientes_a_crear_ahora)):
                nombre = fake.first_name()
                apellido = fake.last_name()
                
                nombre_email = slugify_email_name(nombre)
                apellido_email = slugify_email_name(apellido)
                email_domain = fake.free_email_domain()
                
                # Usamos el conteo existente para evitar colisiones de email
                email_formats = [
                    f"{nombre_email}.{apellido_email}{clientes_existentes + i}@{email_domain}",
                    f"{nombre_email[0]}{apellido_email}{clientes_existentes + i}@{email_domain}",
                ]
                correo = random.choice(email_formats)
                
                usuario = Usuario(
                    correo=correo,
                    nombre=nombre,
                    apellido=apellido,
                    telefono=fake.phone_number()[:15],
                    rol='CLIENTE',
                    is_active=True
                )
                usuario.set_password('demo123')
                usuarios_creados.append(usuario)
                
                clientes_creados.append(
                    Cliente(
                        usuario=usuario,
                        ciudad=fake.city(),
                        codigo_postal=fake.postcode()
                    )
                )
            
            Usuario.objects.bulk_create(usuarios_creados)
            for i, cliente in enumerate(clientes_creados):
                cliente.usuario_id = usuarios_creados[i].id
            Cliente.objects.bulk_create(clientes_creados)
            self.stdout.write(self.style.SUCCESS(f'Se crearon {clientes_a_crear_ahora} clientes.'))
        # --- FIN DEL CAMBIO ---


        # --- 2. CREAR PRODUCTOS (Conteo Inteligente) ---

        # --- Obtener el último ID de producto ---
        ultimo_producto = Producto.objects.order_by('-id').first()
        ultimo_id = ultimo_producto.id if ultimo_producto else 0
        # --- FIN DEL CAMBIO ---

        self.stdout.write(f'Creando {PRODUCTOS_A_CREAR} productos nuevos (iniciando desde el ID {ultimo_id + 1})...')
        categorias = list(Categoria.objects.filter(estado=True))
        if not categorias:
            self.stdout.write(self.style.ERROR('Error: No existen categorías activas. No se pueden crear productos.'))
            return
            
        productos_creados = []
        for i in tqdm(range(PRODUCTOS_A_CREAR)):
            nombre_base = random.choice(NOMBRES_PRODUCTOS)
            marca = random.choice(MARCAS)
            nombre_producto = f"{nombre_base} {marca}"
            
            precio_compra = round(random.uniform(50.0, 800.0), 2)
            precio_venta = round(precio_compra * random.uniform(1.3, 1.8), 2)
            
            # --- CAMBIO AQUÍ: Usar el nuevo ID ---
            nuevo_codigo = f"PROD-{(ultimo_id + i + 1):04d}"
            
            producto = Producto(
                codigo_producto=nuevo_codigo, # <-- Código único
                nombre=nombre_producto,
                descripcion=fake.text(max_nb_chars=150),
                precio_venta=precio_venta,
                precio_compra=precio_compra,
                estado='Disponible',
                stock_actual=random.randint(50, 200),
                ano_garantia=random.choice([0, 1, 2]),
                categoria=random.choice(categorias),
                marca=marca
            )
            productos_creados.append(producto)
            
        Producto.objects.bulk_create(productos_creados)
        # --- FIN DEL CAMBIO ---

        self.stdout.write(self.style.SUCCESS(f'--- Poblamiento completado: {PRODUCTOS_A_CREAR} productos creados ---'))