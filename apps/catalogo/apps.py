from django.apps import AppConfig


class CatalogoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.catalogo'

    def ready(self):
        """
        Se ejecuta cuando Django inicia la aplicación.
        Importa los signals para que se registren automáticamente.
        """
        import apps.catalogo.signals
