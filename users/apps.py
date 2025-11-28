# Django app configuration imports
from django.apps import AppConfig

# DJANGO APPS EXPLAINED:
# Django projects are organized into "apps" - self-contained modules
# Each app has its own models, views, templates, and business logic
# AppConfig class provides app-specific configuration and initialization
#
# APP CONFIGURATION PURPOSES:
# - Set app name and label
# - Configure default field types
# - Register signal handlers
# - Perform app initialization tasks
# - Define app-specific settings


class UsersConfig(AppConfig):
    """
    Configuration class for the users app
    
    APP CONFIGURATION:
    - Defines app-specific settings and behavior
    - Registered in settings.INSTALLED_APPS as 'users.apps.UsersConfig'
    - Alternative: just 'users' (Django auto-discovers this config)
    
    FIELD CONFIGURATION:
    - default_auto_field: sets default primary key type for new models
    - BigAutoField: 64-bit integer (handles larger datasets than AutoField)
    - Django 3.2+ recommendation for future-proofing
    """
    
    # Default primary key field type for models in this app
    # BigAutoField: 64-bit auto-incrementing integer
    # Better than AutoField (32-bit) for apps that might have many records
    default_auto_field = 'django.db.models.BigAutoField'
    
    # App name - must match directory name
    # Used for app discovery and imports
    name = 'users'

    def ready(self):
        """
        App initialization - called when Django starts
        
        READY METHOD PURPOSE:
        - Perform one-time app initialization
        - Import signal handlers (must be after models are loaded)
        - Register custom components
        - Set up app-specific configuration
        
        SIGNAL IMPORT TIMING:
        - Signals must be imported after Django loads models
        - ready() is the correct place for signal registration
        - Importing signals in models.py or views.py can cause issues
        
        IMPORT PATTERN:
        - Import inside ready() to avoid circular imports
        - Use module-level import, not function-level for performance
        """
        # Import signal handlers to register them with Django
        # This connects our signal functions to Django's signal system
        import users.signals  # noqa: F401 (ignore unused import warning)
