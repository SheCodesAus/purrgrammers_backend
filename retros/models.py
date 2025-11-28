from django.db import models
from django.contrib.auth import get_user_model

# this retrieves the custom user instead of Django's default user
User = get_user_model()

# related_name creates a reverse relationship for querying backwards
class RetroBoard(models.Model):
    """
    Main retrospective session - the container for all retro activities
    Each board can be assigned to multiple teams for collaboration
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # who created this board. ForeignKey = many boards can have the same creator
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_boards')
    # auto_now_add = sets timestamp once on creation, auto_now = updates on every save
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Soft delete - never actually delete boards (business requirement)
    is_active = models.BooleanField(default=True)
    # Many-to-many: one board can be assigned to multiple teams, one team can have multiple boards
    assigned_teams = models.ManyToManyField('teams.Team', blank=True, related_name='retro_boards')

    def __str__(self):
        # What shows up in Django admin and when printing the object
        return self.title
    

    def get_user_vote_count(self, user):
        """Return number of votes user has cast on board"""
        return user.get_board_vote_count(self)
    
    def get_user_remaining_votes(self, user, max_votes=5):
        """REturn number of votes remaining"""
        return user.get_remaining_board_votes(self, max_votes)
    
    def get_total_votes(self):
        """Return total number of votes cast on this entire board"""
        # Complex query: votes -> cards -> columns -> retro_board (following relationships backward)
        return Vote.objects.filter(card__column__retro_board=self).count()

    def get_board_vote_summary(self):
        """Return voting statistics for this board"""
        from django.db.models import Count
        return {
            'total_votes': self.get_total_votes(),
            'total_cards': Card.objects.filter(column__retro_board=self).count(),
            # Annotate adds a calculated field (vote_count) to each card
            'most_voted_cards': Card.objects.filter(
                column__retro_board=self
            ).annotate(
                vote_count=Count('votes')
            ).order_by('-vote_count')[:5]  # Top 5 most voted cards
        }

    # this automatically returns boards with the newest first
    class Meta:
        ordering = ['-created_at']  # Minus sign = descending order (newest first)

class Column(models.Model):
    """
    Columns within a retro board (e.g., "Start", "Stop", "Continue")
    Each board has multiple columns, each column contains multiple cards
    """
    # Predefined retrospective column types for consistency
    COLUMN_TYPES = [
        ('start', 'Start'),
        ('stop', 'Stop'), 
        ('continue', 'Continue'),
        ('custom', 'Custom'),  # Keeps flexibility for custom names
    ]

    # ForeignKey = one board can have many columns
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
    """
    Individual feedback items - can be in a column or in the "pool" (draft state)
    Users create cards with their thoughts/feedback
    """
    # null=True, blank=True allows cards to exist without a column (in pool/draft state)
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='cards', null=True, blank=True)
    # Direct relationship to retro_board for easier queries (avoids joining through column)
    retro_board = models.ForeignKey(RetroBoard, on_delete=models.CASCADE, related_name='all_cards', null=True, blank=True)
    content = models.TextField(blank=True)
    # Who created this card (no null=True means card must have an owner)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_boards')
    # auto_now_add = sets timestamp once on creation, auto_now = updates on every save
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # For ordering cards within a column
    position = models.PositiveIntegerField(default=0)
    # Privacy option - cards can be anonymous
    is_anonymous = models.BooleanField(default=False)

    # Card workflow: draft (in pool) -> placed (in column)
    STATUS_CHOICES = [
        ('draft', 'Draft'),      # Card in pool (not assigned to column)
        ('placed', 'Placed'),    # Card placed in a column
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        if self.column:
            return f"{self.column.title}: {self.content[:50]}..."
        return f"Pool card: {self.content[:50]}..." # For cards in pool without column
    
    # helper for calculating vote counts without having to call a method. Always accurate and up to date
    @property
    def vote_count(self):
        """Return total number of votes for this card"""
        # Property = accessed like an attribute (card.vote_count) but calculated dynamically
        return self.votes.count()
    
    class Meta:
        ordering = ['position', 'created_at']
        # Ensures no two cards have same position in same column
        unique_together = ['column', 'position']

class Vote(models.Model):
    """
    Voting system - users can vote on important cards
    Each user gets limited votes per retro board (usually 5)
    """
    # ForeignKey = one card can have many votes
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='votes')
    # ForeignKey = one user can cast many votes (across different cards)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} voted for: {self.card.content[:30]}..." 
    
    class Meta:
        ordering = ['-created_at']  # Newest votes first
        # Database index for faster queries when checking user votes on cards
        indexes = [
            models.Index(fields=['user', 'card'], name='retros_vote_user_card_idx'),
        ]
    
class Comment(models.Model):
    """
    Discussion/comments on cards - for deeper conversation about feedback
    """
    # ForeignKey = one card can have many comments
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='comments')
    # ForeignKey = one user can write many comments
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Privacy option like cards
    is_anonymous = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} commented on: {self.card.content[:20]}..."
    
    class Meta:
        ordering = ['created_at'] # shows the comments in chronological order