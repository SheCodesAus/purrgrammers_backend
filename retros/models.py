from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# related_name creates a reverse relationship for querying backwards
class RetroBoard(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_boards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
    
    # this automatically returns boards with the newest first
    class Meta:
        ordering = ['-created_at']

class Column(models.Model):
    COLUMN_TYPES = [
        ('start', 'Start Doing'),
        ('stop', 'Stop Doing'),
        ('keep', 'Keep Doing'),
        ('more', 'More Of'),
        ('less', 'Less Of'),
        ('custom', 'Custom'),
    ]

    retro_board = models.ForeignKey(RetroBoard, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=100)
    column_type = models.CharField(max_length=10, choices=COLUMN_TYPES, default='custom')
    position = models.PositiveIntegerField(default=0) # only allows positive positions (0,1,2,3)
    color = models.CharField(max_length=7, default='#3B82F6') # hex color code
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.retro_board.title} - {self.title}"
    
    class Meta:
        ordering = ['position'] # returns columns in position order: 0, 1, 2, 3 ...
        unique_together = ['retro_board', 'position'] # stops different columns from having the same positions

class Card(models.Model):
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='cards')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    position = models.PositiveIntegerField(default=0)
    is_anonymous = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.column.title}: {self.content[:50]}..." # string slicing to only take 50 first characters which would be messy
    
    # helper for calculating vote counts without having to call a method. Always accurate and up to date
    @property
    def vote_count(self):
        """Return total number of votes for this card"""
        return self.votes.count()
    
    class Meta:
        ordering = ['position', 'created_at']
        unique_together = ['column', 'position']

class Vote(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} voted for: {self.card.content[:30]}..." 
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'card'], name='retros_vote_user_card_idx'),
        ]
    
class Comment(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_anonymous = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} commented on: {self.card.content[:20]}..."
    
    class Meta:
        ordering = ['created_at'] # shows the comments in chronological order