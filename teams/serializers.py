from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.serializers import CustomUserSerializer
from .models import Team, TeamMembership

User = get_user_model()

class TeamMembershipSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    added_by = CustomUserSerializer(read_only=True)

    class Meta:
        model = TeamMembership
        fields = ['id', 'user', 'joined_at', 'added_by']
        read_only_fields = ['id', 'joined_at']

class TeamSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True)
    memberships = TeamMembershipSerializer(many=True, read_only=True)
    members = CustomUserSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team 
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'updated_at', 'is_active', 'memberships', 'members', 'member_count']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        """Return the number of active members in the team"""
        return obj.members.count()
    
    def create(self, validated_data):
        """Override create to set created_by from request user"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class TeamMembershipCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True)
    team_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TeamMembership
        fields = ['user_id', 'team_id']


    def validate_user_id(self, value):
        """Ensure user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return value
    
    def validate_team_id(self, value):
        """Ensure team exists"""
        try:
            Team.objects.get(id=value)
        except Team.DoesNotExist:
            raise serializers.ValidationError("Team does not exist")
        return value
    
    def validate(self, data):
        """Check if membership already exists"""
        if TeamMembership.objects.filter(
            team_id=data['team_id'],
            user_id=data['user_id']
        ).exists():
            raise serializers.ValidationError("User is already a member of this team")
        return data
    
    def create(self, validated_data):
        """Create membership with added_by from request user"""
        validated_data['added_by'] = self.context['request'].user
        user = User.objects.get(id=validated_data.pop('user_id'))
        team = Team.objects.get(id=validated_data.pop('team_id'))

        return TeamMembership.objects.create(user=user, team=team, **validated_data)
    
class TeamListSerializer(serializers.ModelSerializer):
    """For team lists"""
    created_by = CustomUserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'member_count']

    def get_member_count(self, obj):
        return obj.members.count()