from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import UserProfile

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = UserProfile
        fields = ['bio', 'location', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class SimpleTeamSerializer(serializers.Serializer):
    """Simple team serializer to avoid circular imports"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    created_at = serializers.DateTimeField()

class CustomUserSerializer(serializers.ModelSerializer):
    initials = serializers.ReadOnlyField() # includes the initials property for frontend avatars
    profile = UserProfileSerializer(read_only=True)
    teams = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'initials', 'created_at', 'profile', 'teams']
        read_only_fields = ['id', 'created_at']
    
    def get_teams(self, obj):
        """Get teams user is a member of"""
        teams = obj.teams.filter(is_active=True)
        return SimpleTeamSerializer(teams, many=True).data

# separate serializer for user registration: more maintainable, easier to test and keeps logic simpler
class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, data):
        """Check that passwords match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def create(self, validated_data):
        """Create user with basic password - no min length or other restrictions yet"""
        validated_data.pop('password_confirm') # this removes the password_confirm because its not needed for user creation

        # basic create user for now - TODO: add min length / encryption
        user = User.objects.create_user(**validated_data)
        return user

class EmailOrUsernameLoginSerializer(serializers.Serializer): 
    """Serializer for email/username login function"""

    # inherits from serializers.Serializer instead of ModelSerializer as we are not creating/updating a model

    username = serializers.CharField() # accepts a string that can be either username or email
    password = serializers.CharField(style={'input_type': 'password'}) # renders as password field

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )

            if not user:
                raise serializers.ValidationError(
                    'Unable to login with provided credentials',
                    code='authorization'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'User account is disabled',
                    code='authorization'
                )
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Must include "username" and "password".',
                code='authorization'
            )
