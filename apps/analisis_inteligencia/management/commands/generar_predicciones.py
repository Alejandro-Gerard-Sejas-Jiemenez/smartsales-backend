from django.core.management.base import BaseCommand
from apps.catalogo.models import Categoria
from apps.analisis_inteligencia.utils import (
    train_model_for_category, 
    predict_future_for_category,
    save_predictions_to_db
)

class Command(BaseCommand):
    help = 'Entrena el modelo de IA y genera predicciones de ventas por categoría'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando Proceso de Predicción de Ventas ---'))
        
        categorias = Categoria.objects.filter(estado=True)
        
        for cat in categorias:
            self.stdout.write(self.style.NOTICE(f'Procesando Categoría: {cat.nombre}...'))
            
            # 1. Entrenar (o cargar) el modelo
            # (train_model_for_category ya guarda el modelo .joblib)
            _, model_path = train_model_for_category(cat.id)
            
            if model_path is None:
                self.stdout.write(self.style.WARNING(f'No se pudo entrenar el modelo para {cat.nombre}. Saltando.'))
                continue

            # 2. Predecir los próximos 90 días
            df_predicciones = predict_future_for_category(cat.id, dias_a_predecir=90)
            
            if df_predicciones is None:
                self.stdout.write(self.style.ERROR(f'Falló la predicción para {cat.nombre}.'))
                continue
                
            # 3. Guardar en la Base de Datos
            save_predictions_to_db(cat.id, df_predicciones)
            
            self.stdout.write(self.style.SUCCESS(f'Predicciones para {cat.nombre} guardadas.'))

        self.stdout.write(self.style.SUCCESS('--- Proceso de Predicción Terminado ---'))