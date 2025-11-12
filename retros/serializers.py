from rest_framework import serializers
from users.serializers import CustomUserSerializer
from .models import RetroBoard, Column, Card, Vote, Comment

class RetroBoardSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True) # for GET requests. Returns full user object with all details
    created_by_id = serializers.IntegerField(write_only=True, required=False) # for POST requests - just user id
    
    class Meta:
        model = RetroBoard
        fields = ['id', 'title', 'description', 'created_by', 'created_by_id', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        
        validated_data['created_by_id'] = self.context['request'].user.id
        return super().create(validated_data)

class ColumnSerializer(serializers.ModelSerializer):
    retro_board = serializers.PrimaryKeyRelatedField(queryset=RetroBoard.objects.all())
    card_count = serializers.SerializerMethodField() # count of cards in this column

    class Meta:
        model = Column
        fields = ['id', 'retro_board', 'title', 'column_type', 'position', 'color', 'created_at', 'updated_at', 'card_count']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_card_count(self, obj):
        """Return the number of cards in this column"""
        return obj.cards.count()
    
class CardSerializer(serializers.ModelSerializer):
    column = serializers.PrimaryKeyRelatedField(queryset=Column.objects.all()) 
    created_by = CustomUserSerializer(read_only=True) # for GET requests - full user details
    created_by_id = serializers.IntegerField(write_only=True, required=False) # for POST requests, accepts just integer id
    vote_count = serializers.ReadOnlyField() # includes the @property from the model
    user_has_voted = serializers.SerializerMethodField() # checks if current user has already voted on this card

    class Meta:
        model = Card
        fields = ['id', 'column', 'content', 'created_by', 'created_by_id', 'created_at', 'updated_at', 'position', 'is_anonymous', 'vote_count', 'user_has_voted']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # automatically set created_by to current user
        validated_data['created_by_id'] = self.context['request'].user.id
        return super().create(validated_data)
    
    def get_user_has_voted(self, obj):
        """Check if the current user has already voted on this card"""
        # won't work fully until we add user authentication
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.votes.filter(user=request.user).exists()
        return False
    
class VoteSerializer(serializers.ModelSerializer):
    card = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all())
    user = CustomUserSerializer(read_only=True) # for GET requests
    user_id = serializers.IntegerField(write_only=True, required=False) # for POST requests

    class Meta:
        model = Vote
        fields = ['id', 'card', 'user', 'user_id', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        # automatically set user to current user
        validated_data['user_id'] = self.context['request'].user.id
        return super().create(validated_data)
    
    def validate(self, data):
        """ Check that user hasn't already voted on this card"""
        user = self.context['request'].user
        card = data['card']

        if Vote.objects.filter(user=user, card=card).exists():
            raise serializers.ValidationError("You have already voted on this card")
        
        return data
    
class CommentSerializer(serializers.ModelSerializer):
    card = serializers.PrimaryKeyRelatedField(queryset=Card.objects.all())
    user = CustomUserSerializer(read_only=True) # for GET requests
    user_id = serializers.IntegerField(write_only=True, required=False) # for POST requests

    class Meta:
        model = Comment
        fields = ['id', 'card', 'user', 'user_id', 'content', 'created_at', 'updated_at', 'is_anonymous']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # automatically set user to current user
        validated_data['user_id'] = self.context['request'].user.id
        return super().create(validated_data)