from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class RetroBoard(models.Model):
    """
    Main retrospective session - the container for all retro activities
    Each board can be assigned to one team
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_boards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    # One team per board; a team can have multiple boards
    team = models.ForeignKey('teams.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='retro_boards')
    

    def __str__(self):
        
        return self.title
    

    def get_user_vote_count(self, user):
        """Return number of votes user has cast on board"""
        return user.get_board_vote_count(self)
    
    def get_user_remaining_votes(self, user, max_votes=5):
        """REturn number of votes remaining"""
        return user.get_remaining_board_votes(self, max_votes)
    
    def get_total_votes(self):
        """Return total number of votes cast on this entire board"""
        
        return Vote.objects.filter(card__column__retro_board=self).count()

    def get_board_vote_summary(self):
        """Return voting statistics for this board"""
        from django.db.models import Count
        return {
            'total_votes': self.get_total_votes(),
            'total_cards': Card.objects.filter(column__retro_board=self).count(),
            'most_voted_cards': Card.objects.filter(
                column__retro_board=self
            ).annotate(
                vote_count=Count('votes')
            ).order_by('-vote_count')[:5]  
        }
    
    def get_active_voting_round(self):
        """
        Get the current active voting round
        Creates round 1 if no round exists yet
        """

        # try to get active round
        active_round = self.voting_rounds.filter(is_active=True).first()

        if active_round:
            return active_round
        
        # if no active round - creates round one
        # handles boards that were created before I implemented this feature
        return VotingRound.objects.create(
            retro_board=self,
            round_number=1,
            is_active=True
        )

    # this automatically returns boards with the newest first
    class Meta:
        ordering = ['-created_at']  # Minus sign = descending order (newest first)

class VotingRound(models.Model):
    """
    Tracks voting rounds per board
    Each round gives users another 5 votes to use
    Cards show cumulative total of votes over the rounds
    """

    retro_board = models.ForeignKey(
        RetroBoard,
        on_delete=models.CASCADE,
        related_name='voting_rounds',
    )

    round_number = models.PositiveIntegerField(default=1) # each new board is round 1
    is_active = models.BooleanField(default=True) # only one active round per board
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Active" if self.is_active else "Closed"
        return f"{self.retro_board.title} - Round {self.round_number} ({status})"
    
    class Meta:
        ordering = ['round_number']
        # prevent duplicate round numbers on the same board
        unique_together = ['retro_board', 'round_number']

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

class Tag(models.Model):
    """
    Predefined tags for cards with a custom option if needed
    """
    TAG_CHOICES = [

        # NOTE: these are easily changeable if we want different ones
        # languages
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('java', 'Java'),
        ('csharp', 'C#'),
        ('typescript', 'TypeScript'),

        # frameworks
        ('django', 'Django'),
        ('nodejs', 'Node.js'),
        ('react', 'React'),
        ('angular', 'Angular'),

        # other
        ('tools', 'Tools'),
        ('team_culture', 'Team Culture'),
        ('workload', 'Workload'),
        ('communication', 'Communication'),

        # we don't have to implement this one, just adding it in case
        ('custom', 'Custom'),
    ]

    name = models.CharField(max_length=50, choices=TAG_CHOICES, unique=True)
    
    def __str__(self):
        return self.get_name_display()
    
    class Meta:
        ordering = ['name']

class Card(models.Model):
    """
    Individual feedback items - can be in a column or in the "pool" (draft state)
    Users create cards with their thoughts/feedback
    """
    
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='cards', null=True, blank=True)
    retro_board = models.ForeignKey(RetroBoard, on_delete=models.CASCADE, related_name='all_cards', null=True, blank=True)
    content = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_cards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    position = models.PositiveIntegerField(default=0)
    is_anonymous = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True, related_name='cards')

    # Card workflow: draft (in pool) -> placed (in column)
    STATUS_CHOICES = [
        ('draft', 'Draft'),      # Card in pool (not assigned to column)
        ('placed', 'Placed'),    # Card placed in a column
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        if self.column:
            return f"{self.column.title}: {self.content[:50]}..."
        return f"Pool card: {self.content[:50]}..." # For cards in pool without column TODO: Emma delete?

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
    voting_round = models.ForeignKey(
        VotingRound,
        on_delete=models.CASCADE,
        related_name='votes',
        null=True, # allows existing votes to not have round temporarily
        blank=True
    )
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

class ActionItem(models.Model):
    """
    Action items for tracking tasks from retro boards

    Separate model instead of adding optional fields to card model
    - Exists independently after retro ends and board is closed
    - Has its own status workflow: todo -> in_progress -> completed
    - Can be assigned to team members

    User flow:
    1. User creates action item from the board page
    2. User updates status as work progresses
    3. User can assign to team members for accountability
    """

    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    # which board this action belongs to:
    retro_board = models.ForeignKey(
        RetroBoard,
        on_delete=models.CASCADE,
        related_name='action_items'
    )

    # action item content
    content = models.TextField()

    # tracking progress with todo -> in progress -> completed
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo'
    )

    # who created the action item
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_action_items'
    )

    # optional - assign to a team member for accountability - users can assign themselves
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,        # Database allows NULL
        blank=True,       # Forms/API don't require it
        related_name='assigned_action_items'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Action: {self.content[:50]}... ({self.status})" # slice prevents super long text, ... indicates text has been truncated
    
    class Meta:
        ordering = ['created_at']