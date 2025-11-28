# Django signals - automatic actions triggered by model events
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

# DJANGO SIGNALS EXPLAINED:
# Signals allow decoupled applications to get notified when actions occur
# Common signals: pre_save, post_save, pre_delete, post_delete
# Signals help maintain data consistency and trigger related actions
#
# WHY USE SIGNALS?
# - Automatic actions without manual intervention
# - Keep business logic decoupled from views
# - Ensure data consistency across related models
# - Better than overriding save() method (works with bulk operations)

# SIGNAL REGISTRATION:
# @receiver decorator registers function to handle specific signal
# sender parameter specifies which model triggers the signal
# Signal handlers run in the same database transaction as the triggering action

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile when a new User is created
    
    SIGNAL PARAMETERS:
    - sender: the model class that sent the signal (User)
    - instance: the specific model instance being saved
    - created: Boolean indicating if this is a new instance
    - **kwargs: additional signal parameters
    
    BUSINESS LOGIC:
    - Only create profile for newly created users (created=True)
    - Don't create profile on user updates (created=False)
    - Ensures every user has a profile without manual intervention
    
    WHY AUTOMATIC PROFILE CREATION?
    - Simplifies user registration process
    - Prevents errors when accessing user.profile
    - Consistent user experience
    - Reduces boilerplate code in views
    
    ALTERNATIVE APPROACHES:
    1. Create profile in registration view (couples logic to view)
    2. Create profile on first access (get_or_create pattern)
    3. Use signals (current approach - cleaner separation)
    """
    if created:  # Only for newly created users, not updates
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Automatically save UserProfile when User is saved
    
    PROFILE SYNCHRONIZATION:
    - Ensures profile is saved when user is updated
    - Maintains data consistency between User and UserProfile
    - Handles cases where User and Profile are updated together
    
    DEFENSIVE PROGRAMMING:
    - hasattr() check prevents errors if profile doesn't exist
    - Could happen in edge cases or during migrations
    - Safer than assuming profile always exists
    
    WHEN THIS TRIGGERS:
    - User information is updated (first_name, last_name, etc.)
    - Admin updates user through Django admin
    - Bulk user updates through management commands
    - Any save() call on User model
    
    POTENTIAL ISSUES:
    - Could create unnecessary database queries
    - Consider adding conditions to only save when needed
    - Profile might not need saving on every user save
    
    NOTE: This signal may be redundant if profile is only updated
    through dedicated profile endpoints. Consider removing if not needed.
    """
    # Check if user has profile before trying to save it
    # Prevents AttributeError in edge cases
    if hasattr(instance, 'profile'):
        instance.profile.save()