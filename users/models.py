# Django imports for database models and user authentication
from django.db import models
from django.contrib.auth.models import AbstractUser

# DJANGO USER AUTHENTICATION EXPLAINED:
# Django comes with a built-in User model (django.contrib.auth.models.User)
# However, it's recommended to create a custom user from the start of a project
# AbstractUser provides all the default Django User fields and methods
# while allowing us to add custom fields and behaviors

# WHY USE AbstractUser instead of User?
# 1. Future-proofing: easier to add fields later without complex migrations
# 2. Project requirements: we need email as unique field (not default)
# 3. Business logic: we need user methods for voting and team relationships
# 4. Avatar functionality: custom initials property for frontend


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    
    DJANGO MODEL CONCEPTS:
    - Models are Python classes that represent database tables
    - Each attribute becomes a database column
    - AbstractUser gives us: username, password, email, first_name, last_name, etc.
    - We're extending it to add business-specific fields and methods
    
    BUSINESS REQUIREMENTS:
    - Email must be unique (for login with email OR username)
    - Track when users joined (created_at)
    - Support avatar generation via initials
    - Handle voting logic for retrospective boards
    """
    
    # FIELD DEFINITIONS:
    # EmailField = CharField with email validation built-in
    # unique=True = enforces database-level uniqueness constraint
    # This allows users to login with either email OR username
    email = models.EmailField(unique=True)
    
    # DateTimeField with auto_now_add=True sets timestamp only on creation
    # This tracks when the user account was created (immutable)
    created_at = models.DateTimeField(auto_now_add=True)

    # INHERITED FROM AbstractUser (we get these for free):
    # - username: CharField(max_length=150, unique=True)
    # - password: CharField(max_length=128) - auto-hashed by Django
    # - first_name: CharField(max_length=150, blank=True)
    # - last_name: CharField(max_length=150, blank=True)
    # - is_active: BooleanField(default=True)
    # - is_staff: BooleanField(default=False)
    # - date_joined: DateTimeField(default=now)
    # Plus authentication methods like check_password(), set_password(), etc.

    def __str__(self):
        """
        String representation of the User object
        
        DJANGO CONCEPT: __str__ method
        - Called when object is printed or displayed in Django admin
        - Should return a human-readable string identifying the object
        - Best practice: return the most recognizable field (username for users)
        - Used in: Django admin, shell, debugging, foreign key displays
        """
        return self.username
    
    def get_board_vote_count(self, retro_board, voting_round=None):
        """
        Return total number of votes user has cast on specific retro board
        
        BUSINESS LOGIC: Vote counting for retrospective sessions
        - Each user has a limit of votes per voting round (usually 5)
        - This method counts how many votes they've already used
        - If voting_round is provided, counts only that round's votes
        - If voting_round is None, counts ALL votes (for cumulative totals)
        
        DJANGO ORM CONCEPTS:
        - self.votes: uses reverse relationship (related_name='votes' in Vote model)
        - filter(): creates a QuerySet with specified conditions
        - card__column__retro_board: follows ForeignKey relationships using double underscores
        - count(): returns number of matching records (more efficient than len())
        
        RELATIONSHIP CHAIN:
        User -> Vote -> Card -> Column -> RetroBoard
        """
        queryset = self.votes.filter(
            card__column__retro_board=retro_board
        )
        # If specific round provided, filter by that round
        if voting_round is not None:
            queryset = queryset.filter(voting_round=voting_round)
        return queryset.count()
    
    def get_remaining_board_votes(self, retro_board, max_votes=5):
        """
        Return number of votes user has remaining for CURRENT voting round
        
        BUSINESS LOGIC: Vote limit enforcement per round
        - Default limit: 5 votes per user per ROUND (not per board)
        - Each new round gives users fresh votes
        - Uses board's active voting round automatically
        
        PYTHON CONCEPTS:
        - Default parameter: max_votes=5 (can be overridden if needed)
        - max(0, calculation): ensures we never return negative numbers
        - Method chaining: uses get_board_vote_count() method we defined above
        
        USAGE:
        - Frontend: show "X votes remaining" to users
        - API validation: prevent voting when limit reached
        """
        # Get the current active round for this board
        active_round = retro_board.get_active_voting_round()
        # Count votes only for the current round
        used_votes = self.get_board_vote_count(retro_board, voting_round=active_round)
        return max(0, max_votes - used_votes)
    
    def can_vote_on_board(self, retro_board, max_votes=5):
        """
        Check if user can cast another vote in the current voting round
        
        BUSINESS LOGIC: Permission checking per round
        - Returns True/False for vote permission
        - Checks against CURRENT ROUND's vote count only
        - Each new round resets this check
        
        PYTHON CONCEPTS:
        - Boolean return: True if can vote, False if limit reached
        - Comparison operator: < returns Boolean
        - Method reuse: leverages get_remaining_board_votes() for consistency
        """
        return self.get_remaining_board_votes(retro_board, max_votes) > 0
    
    
    # FRONTEND INTEGRATION: Avatar Generation
    # This property provides data for avatar generation using DiceBear API
    # DiceBear creates consistent, colorful avatars based on initials
    # Frontend can use this to show user avatars without image uploads
    
    @property
    def initials(self):
        """
        Return user initials for avatar generation via DiceBear on frontend
        
        PYTHON CONCEPTS:
        - @property decorator: makes method accessible like an attribute
        - Access as user.initials (not user.initials())
        - Calculated dynamically each time it's accessed
        - Read-only property (no setter defined)
        
        STRING SLICING:
        - string[0]: first character
        - string[:2]: first two characters
        - .upper(): converts to uppercase
        
        LOGIC FLOW:
        1. First preference: first letter of first + last name
        2. Fallback: first two letters of first name only
        3. Final fallback: first two letters of username
        
        FRONTEND USAGE:
        - DiceBear API: https://avatars.dicebear.com/api/initials/AB.svg
        - Consistent colors based on initials
        - No need for image uploads or storage
        """
        if self.first_name and self.last_name:
            # Best case: use first letter of each name (e.g., "John Doe" -> "JD")
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            # Fallback: use first 2 letters of first name (e.g., "John" -> "JO")
            return self.first_name[:2].upper()
        # Final fallback: use first 2 letters of username (e.g., "johndoe" -> "JO")
        return self.username[:2].upper()


class UserProfile(models.Model):
    """
    Extended user profile information - separate model for optional user data
    
    DJANGO DESIGN PATTERN: Profile Model
    - Keep authentication fields in User model (username, email, password)
    - Put optional/extended fields in separate Profile model
    - Benefits: cleaner User model, optional profile creation, easier permissions
    
    ONE-TO-ONE RELATIONSHIP:
    - Each User has exactly one Profile
    - Each Profile belongs to exactly one User
    - Like a 1:1 extension of the User table
    
    BUSINESS LOGIC:
    - Bio: user description for team collaboration
    - Location: helps with team formation and time zones
    - Timestamps: track profile creation and updates
    """
    
    # OneToOneField creates 1:1 relationship with CustomUser
    # on_delete=CASCADE: delete profile when user is deleted
    # related_name='profile': access profile as user.profile
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # TextField: longer text field for user bio/description
    # max_length=500: limit bio length for UI/UX purposes
    # blank=True: field can be empty in forms (not required)
    bio = models.TextField(max_length=500, blank=True)
    
    # CharField: short text field for location
    # blank=True: optional field
    location = models.CharField(max_length=100, blank=True)
    
    # CharField: job role/title
    # blank=True: optional field
    job_role = models.CharField(max_length=100, blank=True)
    
    # Timestamp fields for audit trail
    # auto_now_add=True: set once on creation
    # auto_now=True: update every time model is saved
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """
        String representation of UserProfile object
        
        DJANGO CONCEPT: Model __str__ method
        - Shows in Django admin interface
        - Used in debugging and shell sessions
        - Should be descriptive and unique
        
        F-STRING USAGE:
        - f"{variable}'s Profile": modern Python string formatting
        - Cleaner than .format() or % formatting
        - Evaluates expressions inside {}
        
        RELATIONSHIP ACCESS:
        - self.user: accesses related User object
        - .username: accesses field on related User
        """
        return f"{self.user.username}'s Profile"




