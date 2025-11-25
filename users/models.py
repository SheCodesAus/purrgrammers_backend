from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # don't need to add username as it is provided by default
    # first_name and last_name also included, this is where the initials avatar gets its info

    def __str__(self):
        return self.username
    
    def get_board_vote_count(self, retro_board):
        """Return total number of votes user has cast on specific board"""
        # using reverse relationship from user to vote
        return self.votes.filter(
            card__column__retro_board=retro_board
        ).count()
    
    def get_remaining_board_votes(self, retro_board, max_votes=5):
        """Return number of votes user has remaining on this board"""
        used_votes = self.get_board_vote_count(retro_board)
        return max(0, max_votes - used_votes)
    
    def can_vote_on_board(self, retro_board, max_votes=5):
        """Check if user can cast another vote"""
        return self.get_board_vote_count(retro_board) < max_votes 
    
    
    # this is a helper for the frontend to generate initial avatars using DiceBear
    
    @property
    def initials(self):
        """Return user initials for avatar generation via dicebear on frontend"""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper() # uses index to get the first letter of first and last name
        elif self.first_name:
            return self.first_name[:2].upper() # fallback, uses first 2 letters of first name
        return self.username[:2].upper() # final fallback, first two letters or username
    
       
