# Django model imports
from django.db import models
from django.contrib.auth import get_user_model

# TEAM MANAGEMENT SYSTEM:
# Teams are groups of users who collaborate on retrospective boards
# Features:
# - Team creation and management
# - Member invitation and removal
# - Team-based board assignment
# - Audit trail for membership changes or data collection
#
# BUSINESS REQUIREMENTS:
# - Users can belong to multiple teams
# - Teams can have multiple retro boards
# - Track who added each member (audit trail)
# - Soft deletion (is_active field)


# Get custom user model (best practice)
User = get_user_model()

class Team(models.Model):
    """
    Team model for grouping users and organizing retrospective sessions
    
    BUSINESS LOGIC:
    - Teams organize users for collaborative retro sessions
    - Team creators can manage membership and boards
    - Teams can be assigned to multiple retro boards
    - Soft deletion preserves historical data
    
    RELATIONSHIPS:
    - created_by: ForeignKey to User (team owner/admin)
    - members: ManyToMany to User through TeamMembership
    - retro_boards: ManyToMany from RetroBoard (reverse relationship)
    """
    
    # Basic team information
    name = models.CharField(max_length=200)  # Team name (required)
    description = models.TextField(blank=True)  # Optional team description
    
    # TEAM OWNERSHIP:
    # ForeignKey creates many-to-one relationship (many teams can have same creator)
    # on_delete=CASCADE: delete team when creator is deleted
    # related_name='created_teams': access via user.created_teams.all()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_teams')
    
    # TEAM MEMBERSHIP - MANY-TO-MANY RELATIONSHIP:
    # Complex many-to-many with additional data (when joined, who added them)
    # through='TeamMembership': use custom intermediate model
    # through_fields: specify which fields link Team and User
    # related_name='teams': access user's teams via user.teams.all()
    members = models.ManyToManyField(
        User, 
        through='TeamMembership',  # Custom intermediate model
        through_fields=('team', 'user'),  # Specify linking fields
        related_name='teams'  # Reverse relationship name
    )
    
    # Audit trail timestamps
    created_at = models.DateTimeField(auto_now_add=True)  # Set once on creation
    updated_at = models.DateTimeField(auto_now=True)      # Update on every save
    
    # SOFT DELETION:
    # Instead of deleting teams, mark as inactive
    # Preserves historical data and relationships
    # Allows "undeleting" teams if needed
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """
        String representation of Team object
        
        USAGE:
        - Django admin interface
        - Debugging and logging
        - Shell sessions
        - Foreign key displays
        """
        return self.name
    
    class Meta:
        """
        Model metadata and configuration
        
        ORDERING:
        - Default queryset ordering (newest teams first)
        - '-created_at': descending order (minus sign)
        - Affects admin interface and default queries
        """
        ordering = ['-created_at']  # Newest teams first

class TeamMembership(models.Model):
    """
    Through model for Team-User many-to-many relationship with additional data
    
    THROUGH MODEL PATTERN:
    - Adds extra fields to many-to-many relationships
    - Stores metadata about the relationship itself
    - Required when you need more than just the link between objects
    
    WHY THROUGH MODEL?
    - Track when user joined team (audit trail)
    - Track who added the user (accountability)
    - Support future features (roles, permissions, etc.)
    - Enable membership history and analytics
    
    BUSINESS VALUE:
    - Audit compliance (who added whom, when)
    - Team analytics (membership growth, turnover)
    - Troubleshooting membership issues
    - Potential role-based permissions
    """
    
    # CORE RELATIONSHIP FIELDS:
    # Links to both Team and User models
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_memberships')
    
    # MEMBERSHIP METADATA:
    # When did this user join this team?
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # Who added this user to the team?
    # null=True: allows system-generated memberships
    # SET_NULL: preserve membership even if adder is deleted
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_memberships')

    def __str__(self):
        """
        String representation showing user and team relationship
        
        FORMAT: "username in Team Name"
        Clearly shows the membership relationship
        """
        return f"{self.user.username} in {self.team.name}"
    
    class Meta:
        """
        TeamMembership model configuration
        
        UNIQUE_TOGETHER:
        - Prevents duplicate memberships (user can't join same team twice)
        - Database-level constraint for data integrity
        - Tuple format: (field1, field2)
        
        ORDERING:
        - Default sort by join date (oldest memberships first)
        - Useful for membership history and seniority
        """
        unique_together = ['team', 'user']  # Prevent duplicate memberships
        ordering = ['joined_at']  # Oldest memberships first
    
