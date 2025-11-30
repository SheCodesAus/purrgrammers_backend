# Django REST Framework serializer imports
from rest_framework import serializers
# Django authentication imports
from django.contrib.auth import get_user_model
# Import user serializer for nested data
from users.serializers import CustomUserSerializer
# Import our team models
from .models import Team, TeamMembership

# SERIALIZER ARCHITECTURE:
# Multiple serializers for different use cases:
# 1. TeamMembershipSerializer: detailed membership info
# 2. TeamSerializer: full team data with members
# 3. TeamMembershipCreateSerializer: for adding members
# 4. TeamListSerializer: lightweight team list
#
# WHY MULTIPLE SERIALIZERS?
# - Different endpoints need different data levels
# - Performance optimization (don't load unnecessary data)
# - Separation of concerns (read vs write operations)
# - Flexible API design for frontend needs

User = get_user_model()

class TeamMembershipSerializer(serializers.ModelSerializer):
    """
    Detailed team membership serializer with full user information
    
    PURPOSE:
    - Show complete membership details including user info
    - Used for team member lists and membership management
    - Includes audit information (who added, when joined)
    
    NESTED SERIALIZERS:
    - user: full user object with profile and teams
    - added_by: who added this member (audit trail)
    - Both use CustomUserSerializer for consistent user data
    
    API USAGE:
    - GET /api/teams/{id}/members/
    - Team management interfaces
    - Membership audit reports
    """
    
    # NESTED SERIALIZER PATTERN:
    # Include full user object instead of just user ID
    # read_only=True: user info comes from user endpoints, not editable here
    user = CustomUserSerializer(read_only=True)
    added_by = CustomUserSerializer(read_only=True)

    class Meta:
        model = TeamMembership
        
        # FIELD SELECTION:
        # Include: membership metadata and full user objects
        # Exclude: team field (usually obvious from context)
        fields = ['id', 'user', 'joined_at', 'added_by']
        
        # READ-ONLY PROTECTION:
        # id: auto-generated primary key
        # joined_at: timestamp set automatically
        read_only_fields = ['id', 'joined_at']

class TeamSerializer(serializers.ModelSerializer):
    """
    Complete team serializer with members, memberships, and metadata
    
    COMPLEX
    - Multiple nested relationships
    - Calculated fields
    - Custom create logic
    - Performance considerations
    
    USE CASES:
    - Team detail pages
    - Team management interfaces
    - Complete team data for frontend state
    
    PERFORMANCE NOTES:
    - Multiple SerializerMethodFields make database queries
    - Consider using select_related() and prefetch_related() in views
    - May be slow for teams with many members
    """
    
    # NESTED RELATIONSHIPS:
    # created_by: who created the team (full user object)
    created_by = CustomUserSerializer(read_only=True)
    
    # memberships: detailed membership info with join dates and added_by
    # many=True: one team has many memberships
    memberships = TeamMembershipSerializer(many=True, read_only=True)
    
    # members: just the user objects (simpler than memberships)
    # Useful when you just need user list without membership metadata
    members = CustomUserSerializer(many=True, read_only=True)
    
    # CALCULATED FIELDS:
    # SerializerMethodField calls get_member_count() method
    # Provides convenient member count without frontend calculation
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team 
        
        # COMPREHENSIVE FIELD LIST:
        # Basic: id, name, description, timestamps, status
        # Relationships: created_by, memberships, members
        # Calculated: member_count
        fields = [
            'id', 'name', 'description', 'created_by', 
            'created_at', 'updated_at', 'is_active', 
            'memberships', 'members', 'member_count'
        ]
        
        # PROTECTION FROM MODIFICATION:
        # Auto-generated: id, timestamps
        # System-managed: created_by (set in create method)
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        """
        Calculate number of active members in the team
        
        SERIALIZERMETHODFIELD PATTERN:
        - Method name: get_<field_name>
        - obj parameter: the Team model instance
        - Return value becomes field value in API response
        
        DATABASE QUERY:
        - obj.members.count(): efficient COUNT query
        - Only counts active members (through ManyToMany relationship)
        - More efficient than len(obj.members.all())
        
        FRONTEND USAGE:
        - Team cards showing "5 members"
        - Sorting teams by member count
        - Dashboard statistics
        """
        return obj.members.count()
    
    def create(self, validated_data):
        """
        Override create to automatically set team creator and add them as a member
        
        WHY OVERRIDE CREATE?
        - created_by field should be set automatically from authenticated user
        - Security: prevent users from impersonating other team creators
        - UX: users don't need to specify themselves as creator
        - Auto-add creator as first team member
        
        CONTEXT ACCESS:
        - self.context['request']: access to HTTP request object
        - request.user: authenticated user making the request
        - Context is passed from view to serializer
        
        SECURITY CONSIDERATIONS:
        - Only authenticated users can create teams (enforced by view permissions)
        - created_by is always the requesting user (no spoofing)
        - Team ownership determines management privileges
        
        Args:
            validated_data (dict): Clean data from validation
        
        Returns:
            Team: Created team instance with current user as creator and member
        """
        user = self.context['request'].user
        # Set team creator to current authenticated user
        validated_data['created_by'] = user
        # Call parent create method with modified data
        team = super().create(validated_data)
        
        # Automatically add creator as first team member
        TeamMembership.objects.create(
            team=team,
            user=user,
            added_by=user  # They added themselves
        )
        
        return team

class TeamMembershipCreateSerializer(serializers.ModelSerializer):
    """
    Specialized serializer for adding members to teams
    
    PURPOSE:
    - Handle team member addition with validation
    - Separate from main serializers to avoid complexity
    - Write-only serializer (for POST requests only)
    
    DESIGN PATTERN: Write-Only Serializer
    - Only used for creating memberships
    - Uses username for user-friendly input
    - Focused validation for specific use case
    
    VALIDATION LAYERS:
    1. Field validation: username and team_id exist
    2. Cross-field validation: prevent duplicate memberships
    3. Permission validation: handled in view
    """
    
    # WRITE-ONLY FIELDS:
    # Frontend sends username and team ID
    # write_only=True: these fields never appear in responses
    username = serializers.CharField(write_only=True)
    team_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TeamMembership
        # MINIMAL FIELDS:
        # Only include the fields needed for creation
        # Actual User and Team objects are resolved in validation
        fields = ['username', 'team_id']


    def validate_username(self, value):
        """
        Validate that user exists by username
        
        FIELD-LEVEL VALIDATION:
        - Called automatically by DRF during is_valid()
        - Method name: validate_<field_name>
        - Should raise ValidationError if invalid
        
        BUSINESS LOGIC:
        - User must exist in database
        - Clear error message for API consumers
        
        Args:
            value (str): Username from request
        
        Returns:
            str: Validated username
        
        Raises:
            ValidationError: If user doesn't exist
        """
        try:
            User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
    
    def validate_team_id(self, value):
        """
        Validate that team exists and is active
        
        VALIDATION LOGIC:
        - Team must exist in database
        - Could add team.is_active check for business rules
        - Could add permission checks (user can add to this team)
        
        Args:
            value (int): Team ID from request
        
        Returns:
            int: Validated team ID
        
        Raises:
            ValidationError: If team doesn't exist
        """
        try:
            Team.objects.get(id=value)
        except Team.DoesNotExist:
            raise serializers.ValidationError("Team does not exist")
        return value
    
    def validate(self, data):
        """
        Cross-field validation to prevent duplicate memberships
        
        OBJECT-LEVEL VALIDATION:
        - Called after all field-level validation passes
        - Access to all validated field data
        - Check business rules that involve multiple fields
        
        DUPLICATE PREVENTION:
        - Check if user is already a member of the team
        - Prevents database integrity errors
        - Provides user-friendly error message
        
        DATABASE QUERY:
        - filter(): check for existing membership
        - exists(): efficient boolean check (doesn't load objects)
        
        Args:
            data (dict): All validated field data
        
        Returns:
            dict: Validated data if checks pass
        
        Raises:
            ValidationError: If user already in team
        """
        # Look up user by username
        user = User.objects.get(username=data['username'])
        
        # Check for existing membership
        if TeamMembership.objects.filter(
            team_id=data['team_id'],
            user=user
        ).exists():
            raise serializers.ValidationError("User is already a member of this team")
        return data
    
    def create(self, validated_data):
        """
        Create team membership with audit information
        
        CUSTOM CREATION LOGIC:
        1. Set added_by to current user (audit trail)
        2. Convert username to User instance
        3. Create membership with all metadata
        
        AUDIT TRAIL:
        - added_by: tracks who added this member
        - joined_at: automatically set by model
        - Supports accountability and membership history
        
        Args:
            validated_data (dict): Clean data with username and team_id
        
        Returns:
            TeamMembership: Created membership instance
        """
        # Set audit information
        validated_data['added_by'] = self.context['request'].user
        
        # Convert username to User instance
        user = User.objects.get(username=validated_data.pop('username'))
        team = Team.objects.get(id=validated_data.pop('team_id'))

        # Create membership with full objects and audit data
        return TeamMembership.objects.create(
            user=user, 
            team=team, 
            **validated_data  # Includes added_by
        )
    
class TeamListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for team lists and performance-sensitive endpoints
    
    PERFORMANCE OPTIMIZATION:
    - Minimal fields for faster serialization
    - No nested relationships or complex queries
    - Ideal for list views with many teams
    
    USE CASES:
    - Team selection dropdowns
    - Team list pages
    - Dashboard team cards
    - User's teams list
    
    DESIGN PRINCIPLE: Different serializers for different needs
    - List views: minimal data for speed
    - Detail views: complete data for functionality
    - This approach improves API performance and user experience
    """
    
    # Minimal nested data for context
    created_by = CustomUserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        # ESSENTIAL FIELDS ONLY:
        # Enough info for team cards and selection
        # No memberships or detailed member lists
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'member_count']

    def get_member_count(self, obj):
        """
        Efficient member count for list views
        
        PERFORMANCE NOTE:
        - Same query as TeamSerializer.get_member_count()
        - Consider adding prefetch_related('members') in view???
        - Or use annotation in queryset for better performance
        """
        return obj.members.count()