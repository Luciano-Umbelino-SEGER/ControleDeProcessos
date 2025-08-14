from django.apps import AppConfig

class ArquiteturaProcessosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'arquiteturaprocessos'

    def ready(self):
        # Import necessário para registrar os signals
        import arquiteturaprocessos.signals