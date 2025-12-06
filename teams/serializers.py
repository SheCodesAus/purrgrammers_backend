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
    """Detailed team membership serializer with full user information"""
    
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
    """Complete team serializer with members, memberships, and metadata"""
    
    # NESTED RELATIONSHIPS:
    # created_by: who created the team (full user object)
    created_by = CustomUserSerializer(read_only=True)
    
    # memberships: detailed membership info with join dates and added_by
    # many=True: one team has many memberships
    memberships = TeamMembershipSerializer(many=True, read_only=True)
    
    # members: just the user objects (simpler than memberships)
    # Useful when you just need user list without membership metadata
    members = serializers.SerializerMethodField()
    
    # CALCULATED FIELDS:
    # SerializerMethodField calls get_member_count() method
    # Provides convenient member count without frontend calculation
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team 
        
        fields = [
            'id', 'name', 'description', 'created_by', 
            'created_at', 'updated_at', 'is_active', 
            'memberships', 'members', 'member_count'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        """Calculate number of active members in the team"""
        return obj.members.count()
    
    def get_members(self, obj):
        """get members sorted alphabetically"""
        members = obj.members.all().order_by('username')
        return CustomUserSerializer(members, many=True).data

    
    def create(self, validated_data):
        """Override create to automatically set team creator and add them as a member """
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
    """Specialized serializer for adding members to teams"""
    
    # WRITE-ONLY FIELDS:
    # Frontend sends username and team ID
    # write_only=True: these fields never appear in responses
    username = serializers.CharField(write_only=True)
    team_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TeamMembership
        fields = ['username', 'team_id']


    def validate_username(self, value):
        """Validate that user exists by username"""
        try:
            User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
    
    def validate_team_id(self, value):
        """Validate that team exists and is active"""
        try:
            Team.objects.get(id=value)
        except Team.DoesNotExist:
            raise serializers.ValidationError("Team does not exist")
        return value
    
    def validate(self, data):
        """
        Cross-field validation to prevent duplicate memberships
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
    
    """
    
    # Minimal nested data for context
    created_by = CustomUserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'member_count']

    def get_member_count(self, obj):
        return obj.members.count()