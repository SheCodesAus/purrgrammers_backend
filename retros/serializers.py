from rest_framework import serializers
from users.serializers import CustomUserSerializer
from .models import RetroBoard, Column, Card, Vote, Comment

class RetroBoardSerializer(serializers.ModelSerializer):
    """
    Serializer for RetroBoard - handles complex nested data and user-specific fields
    Includes voting info, teams, and columns for complete board view
    """
    created_by = CustomUserSerializer(read_only=True) # for GET requests. Returns full user object with all details
    created_by_id = serializers.IntegerField(write_only=True, required=False) # for POST requests - just user id
    # SerializerMethodField = calculated field that calls a method to get the value
    user_vote_count = serializers.SerializerMethodField()
    user_remaining_votes = serializers.SerializerMethodField()
    max_votes_per_user = serializers.SerializerMethodField()
    assigned_teams = serializers.SerializerMethodField()
    team_count = serializers.SerializerMethodField()
    columns = serializers.SerializerMethodField()
    
    class Meta:
        model = RetroBoard
        # All fields that will be included in API responses
        fields = ['id', 'title', 'description', 'created_by', 'created_by_id', 'created_at', 'updated_at', 'is_active', 'user_vote_count', 'user_remaining_votes', 'max_votes_per_user', 'assigned_teams', 'team_count', 'columns']
        # Fields that can't be modified via API (timestamps, auto-generated IDs)
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Override create to automatically set created_by to current user
        validated_data['created_by_id'] = self.context['request'].user.id
        return super().create(validated_data)
    
    def get_user_vote_count(self, obj):
        """Get current user's total votes on board"""
        # Access request from context to get current user
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Call model method we created
            return obj.get_user_vote_count(request.user)
        return 0
    
    def get_user_remaining_votes(self, obj):
        """Get users remaining votes on board"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_user_remaining_votes(request.user)
        return 5  # Default if not authenticated
    
    def get_max_votes_per_user(self, obj):
        """Retrun the max votes allowed per user (5)"""
        return 5  # Business rule: 5 votes per user per board
    
    def get_assigned_teams(self, obj):
        """Get basic info about assigned teams"""
        # Import here to avoid circular imports (both files importing each other)
        from teams.serializers import TeamListSerializer
        return TeamListSerializer(obj.assigned_teams.all(), many=True).data
    
    def get_team_count(self, obj):
        """Return number of teams assigned to this board"""
        return obj.assigned_teams.count()
    
    def get_columns(self, obj):
        """Get all columns for this board"""
        # Order by position to maintain consistent column order
        columns = obj.columns.all().order_by('position')
        return ColumnSerializer(columns, many=True).data

class ColumnSerializer(serializers.ModelSerializer):
    """
    Serializer for Column - includes cards and card count for frontend convenience
    """
    # PrimaryKeyRelatedField = accepts just the ID of the related object
    retro_board = serializers.PrimaryKeyRelatedField(queryset=RetroBoard.objects.all())
    card_count = serializers.SerializerMethodField() # count of cards in this column
    cards = serializers.SerializerMethodField() # actual cards in this column

    class Meta:
        model = Column
        fields = ['id', 'retro_board', 'title', 'column_type', 'position', 'color', 'created_at', 'updated_at', 'card_count', 'cards']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_card_count(self, obj):
        """Return the number of cards in this column"""
        return obj.cards.count()
    
    def get_cards(self, obj):
        """Return all cards in this column"""
        # Order by position first, then creation time for consistent display
        cards = obj.cards.all().order_by('position', 'created_at')
        # Use CardSerializer but avoid circular import by importing here
        # Pass context so CardSerializer can access current user for voting info
        return CardSerializer(cards, many=True, context=self.context).data
    
class CardSerializer(serializers.ModelSerializer):
    """
    Serializer for Card - handles draft/placed states, voting info, and column colors
    """
    # allow_null=True because cards can be in pool without a column
    column = serializers.PrimaryKeyRelatedField(queryset=Column.objects.all(), required=False, allow_null=True) 
    retro_board = serializers.PrimaryKeyRelatedField(queryset=RetroBoard.objects.all(), required=False, allow_null=True)
    created_by = CustomUserSerializer(read_only=True) # for GET requests - full user details
    created_by_id = serializers.IntegerField(write_only=True, required=False) # for POST requests, accepts just integer id
    vote_count = serializers.ReadOnlyField() # includes the @property from the model
    user_vote_count = serializers.SerializerMethodField() # changed from has_user_voted
    user_board_votes_remaining = serializers.SerializerMethodField() # new field for voting logic update
    color = serializers.SerializerMethodField() # get color from column

    class Meta:
        model = Card
        fields = ['id', 'column', 'retro_board', 'content', 'created_by', 'created_by_id', 'created_at', 'updated_at', 'position', 'is_anonymous', 'status', 'vote_count', 'user_vote_count', 'user_board_votes_remaining', 'color']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_color(self, obj):
        """Get color from the card's column, or default for draft cards"""
        if obj.column:
            return obj.column.color
        return '#94A3B8'  # Default gray for cards in pool (draft state)

    def create(self, validated_data):
        # automatically set created_by to current user
        validated_data['created_by_id'] = self.context['request'].user.id
        
        # Auto-set status based on column presence
        # If card has column = placed, if no column = draft (in pool)
        if 'status' not in validated_data:
            validated_data['status'] = 'placed' if validated_data.get('column') else 'draft'
        
        return super().create(validated_data)
    
    def get_user_vote_count(self, obj):
        """Get number of times current user has voted on card"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Filter votes on this card by current user
            return obj.votes.filter(user=request.user).count()
        return 0
    
    def get_user_board_votes_remaining(self, obj):
        """Get remaining votes for current user on board"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Use the model method from CustomUser
            return request.user.get_remaining_board_votes(obj.column.retro_board)
        return 5  # Default if not authenticated
    
class VoteSerializer(serializers.ModelSerializer):
    """
    Serializer for Vote - includes validation to prevent vote limit exceeded
    """
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
        max_votes = 5  # Business rule

        if current_vote_count >= max_votes:
            # Raise validation error to prevent vote creation
            raise serializers.ValidationError(
                f"You have reached the maximum of {max_votes} for this board. "
                f"You currently have {current_vote_count} votes." 
            )
        
        return data
    
class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for Comment - simple CRUD with automatic user assignment
    """
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