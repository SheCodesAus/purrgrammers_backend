from django.apps import AppConfig


class RetrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'retros'

    def ready(self):
        import retros.signals  # Register signal handlers
