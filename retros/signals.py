# DJANGO SIGNALS - Automatic Actions on Model Changes
# =====================================================
# Signals allow you to execute code automatically when certain database operations occur. This is powerful for business logic
# that should ALWAYS happen, regardless of how the model is created.

from django.db.models.signals import post_save  # Signal fired after model.save()
from django.dispatch import receiver            # Decorator to connect signals to functions
from .models import RetroBoard, Column

# SIGNAL RECEIVER PATTERN
# ========================
# @receiver decorator connects this function to post_save signal
# This means: "Every time a RetroBoard is saved, run this function"
# sender=RetroBoard means: "Only for RetroBoard model, not others"
@receiver(post_save, sender=RetroBoard)
def create_default_columns(sender, instance, created, **kwargs):
    """
    BUSINESS LOGIC: Automatically create 3 default columns when a new RetroBoard is created
    
    WHY USE SIGNALS?
    - Ensures columns are ALWAYS created, regardless of where RetroBoard is created
    - Keeps this logic separate from views/serializers (separation of concerns)
    - Works even if RetroBoard is created via Django admin, scripts, or API
    
    SIGNAL PARAMETERS:
    - sender: The model class that sent the signal (RetroBoard)
    - instance: The actual RetroBoard object that was saved
    - created: Boolean - True if this was a new object, False if updating existing
    - **kwargs: Additional signal data (like raw, using, etc.)
    """
    
    # Only run this expensive operation for NEW boards, not updates
    if created:  # Boolean flag: True = new object, False = existing object updated
        
        # DEFAULT COLUMN CONFIGURATION
        # ==============================
        # Every retrospective needs these 3 standard columns
        # This is a business rule: "All retros must have Start/Stop/Continue"
        default_columns = [
            {
                'title': 'Start',           # Things to start doing
                'column_type': 'start',     # Enum value for type safety
                'position': 0,              # Display order (left to right)
                'color': '#d3bdff'          # Purple theme color
            },
            {
                'title': 'Stop',            # Things to stop doing 
                'column_type': 'stop',      # Enum value for type safety
                'position': 1,              # Middle position
                'color': '#ffd3a8'          # Orange theme color 
            },
            {
                'title': 'Continue',        # Things to keep doing
                'column_type': 'continue',  # Enum value for type safety
                'position': 2,              # Rightmost position
                'color': '#d3bdff'          # Purple theme color
            }
        ]
        
        # BULK CREATION PATTERN
        # =======================
        # Create all columns in a loop rather than individual calls
        # This is more maintainable than 3 separate Column.objects.create() calls
        for column_data in default_columns:
            Column.objects.create(
                retro_board=instance,   # Link to the new board
                **column_data           # Unpack dictionary as keyword arguments
            )