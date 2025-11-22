from rest_framework import serializers
from users.serializers import CustomUserSerializer
from .models import RetroBoard, Column, Card, Vote, Comment

class RetroBoardSerializer(serializers.ModelSerializer):
    created_by = CustomUserSerializer(read_only=True) # for GET requests. Returns full user object with all details
    created_by_id = serializers.IntegerField(write_only=True, required=False) # for POST requests - just user id
    user_vote_count = serializers.SerializerMethodField()
    user_remaining_votes = serializers.SerializerMethodField()
    max_votes_per_user = serializers.SerializerMethodField()
    assigned_teams = serializers.SerializerMethodField()
    team_count = serializers.SerializerMethodField()
    columns = serializers.SerializerMethodField()
    
    class Meta:
        model = RetroBoard
        fields = ['id', 'title', 'description', 'created_by', 'created_by_id', 'created_at', 'updated_at', 'is_active', 'user_vote_count', 'user_remaining_votes', 'max_votes_per_user', 'assigned_teams', 'team_count', 'columns']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        
        validated_data['created_by_id'] = self.context['request'].user.id
        return super().create(validated_data)
    
    def get_user_vote_count(self, obj):
        """Get current user's total votes on board"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_user_vote_count(request.user)
        return 0
    
    def get_user_remaining_votes(self, obj):
        """Get users remaining votes on board"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_user_remaining_votes(request.user)
        return 5
    
    def get_max_votes_per_user(self, obj):
        """Retrun the max votes allowed per user (5)"""
        return 5
    
    def get_assigned_teams(self, obj):
        """Get basic info about assigned teams"""
        # Import here to avoid circular imports
        from teams.serializers import TeamListSerializer
        return TeamListSerializer(obj.assigned_teams.all(), many=True).data
    
    def get_team_count(self, obj):
        """Return number of teams assigned to this board"""
        return obj.assigned_teams.count()
    
    def get_columns(self, obj):
        """Get all columns for this board"""
        columns = obj.columns.all().order_by('position')
        return ColumnSerializer(columns, many=True).data

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
    user_vote_count = serializers.SerializerMethodField() # changed from has_user_voted
    user_board_votes_remaining = serializers.SerializerMethodField() # new field for voting logic update

    class Meta:
        model = Card
        fields = ['id', 'column', 'content', 'created_by', 'created_by_id', 'created_at', 'updated_at', 'position', 'is_anonymous', 'vote_count', 'user_vote_count', 'user_board_votes_remining']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # automatically set created_by to current user
        validated_data['created_by_id'] = self.context['request'].user.id
        return super().create(validated_data)
    
    def get_user_vote_count(self, obj):
        """Get number of times current user has voted on card"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.votes.filter(user=request.user).count()
        return 0
    
    def get_user_board_votes_remaining(self, obj):
        """Get remaining votes for current user on board"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.get_remaining_board_votes(obj.column.retro_board)
        return 5 
    
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
        """Check the user hasn't exceeded 5 votes on the current board"""
        user = self.context['request'].user
        card = data['card']
        retro_board = card.column.retro_board

        # check if user has reached vote limit on this board
        current_vote_count = user.get_board_vote_count(retro_board)
        max_votes = 5

        if current_vote_count >= max_votes:
            raise serializers.ValidationError(
                f"You have reached the maximum of {max_votes} for this board. "
                f"You currently have {current_vote_count} votes." 
            )
        
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