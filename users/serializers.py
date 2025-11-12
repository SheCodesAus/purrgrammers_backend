from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    initials = serializers.ReadOnlyField() # includes the initials property for frontend avatars

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'display_name', 'initials', 'created_at']
        read_only_fields = ['id', 'created_at']

# separate serializer for user registration: more maintainable, easier to test and keeps logic simpler
class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'display_name', 'password', 'password_confirm']

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
