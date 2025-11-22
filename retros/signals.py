from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RetroBoard, Column

@receiver(post_save, sender=RetroBoard)
def create_default_columns(sender, instance, created, **kwargs):
    """
    Automatically create 3 default columns when a new RetroBoard is created
    """
    if created:  # Only run for newly created boards
        default_columns = [
            {
                'title': 'Start',
                'column_type': 'start',
                'position': 0,
                'color': '#d3bdff'
            },
            {
                'title': 'Stop', 
                'column_type': 'stop',
                'position': 1,
                'color': '#ffd3a8'  
            },
            {
                'title': 'Continue',
                'column_type': 'continue',
                'position': 2,
                'color': '#d3bdff'  
            }
        ]
        
        # Create the columns
        for column_data in default_columns:
            Column.objects.create(
                retro_board=instance,
                **column_data
            )