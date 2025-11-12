from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # don't need to add username as it is provided by default
    # first_name and last_name also included, this is where the initials avatar gets its info

    def __str__(self):
        return self.username
    
    # this is a helper for the frontend to generate initial avatars using DiceBear
    
    @property
    def initials(self):
        """Return user initials for avatar generation via dicebear on frontend"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper() # uses index to get the first letter of first and last name
        elif self.first_name:
            return self.first_name[:2].upper() # fallback, uses first 2 letters of first name
        elif self.display_name:
            names = self.display_name.split()
            return ''.join([name[0].upper() for name in names[:2]]) # 2nd fallback, display name initials
        return self.username[:2].upper() # final fallback, first two letters or username
    
