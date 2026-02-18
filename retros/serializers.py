from rest_framework import serializers
from users.serializers import CustomUserSerializer
from django.contrib.auth import get_user_model
from .models import RetroBoard, Column, Card, Vote, Comment, ActionItem, Tag, VotingRound

User = get_user_model()

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
    team = serializers.SerializerMethodField()
    team_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)  # for POST/PUT - accepts team id
    columns = serializers.SerializerMethodField() # columns
    action_items = serializers.SerializerMethodField() # action items
    current_voting_round = serializers.SerializerMethodField() # current active voting round
    
    # Facilitator and permission fields
    is_facilitator = serializers.SerializerMethodField()
    facilitators = serializers.SerializerMethodField()
    can_edit_columns = serializers.SerializerMethodField()
    can_edit_board_title = serializers.SerializerMethodField()
    can_delete_any_card = serializers.SerializerMethodField()
    
    class Meta:
        model = RetroBoard
        # All fields that will be included in API responses
        fields = [
            'id',
            'title',
            'description',
            'created_by',
            'created_by_id',
            'created_at',
            'updated_at',
            'is_active',
            'current_voting_round',
            'user_vote_count',
            'user_remaining_votes',
            'max_votes_per_user',
            'max_votes_per_round',
            'max_votes_per_card',
            'team',
            'team_id',
            'columns',
            'action_items',
            # Facilitator and permission fields
            'is_facilitator',
            'facilitators',
            'participants_can_edit_columns',
            'participants_can_edit_board_title',
            'participants_can_delete_any_card',
            'can_edit_columns',
            'can_edit_board_title',
            'can_delete_any_card',
            'invite_code',
            ]
        # Fields that can't be modified via API (timestamps, auto-generated IDs)
        read_only_fields = ['id', 'created_at', 'updated_at', 'invite_code']
    
    def create(self, validated_data):
        # Override create to automatically set created_by to current user
        validated_data['created_by_id'] = self.context['request'].user.id
        # Handle team_id -> team conversion
        team_id = validated_data.pop('team_id', None)
        if team_id:
            from teams.models import Team
            validated_data['team'] = Team.objects.get(id=team_id)
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Handle team_id -> team conversion for updates
        team_id = validated_data.pop('team_id', None)
        if team_id is not None:
            if team_id:
                from teams.models import Team
                validated_data['team'] = Team.objects.get(id=team_id)
            else:
                validated_data['team'] = None
        return super().update(instance, validated_data)
    
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
        """Return the max votes allowed per user per round"""
        return obj.max_votes_per_round
    
    def get_team(self, obj):
        """Get team info with members for assignee dropdown"""
        if obj.team:
            team = obj.team
            # Get members with just the fields needed for assignee dropdown - alphabetically sorted
            members = team.members.all().order_by('username').values('id', 'username', 'first_name', 'last_name')
            members_with_initials = []
            for member in members:
                initials = ''
                if member['first_name'] and member['last_name']:
                    initials = member['first_name'][0] + member['last_name'][0]
                elif member['username']:
                    initials = member['username'][:2].upper()
                members_with_initials.append({
                    'id': member['id'],
                    'username': member['username'],
                    'first_name': member['first_name'],
                    'last_name': member['last_name'],
                    'initials': initials
                })
            return {
                'id': team.id,
                'name': team.name,
                'members': members_with_initials
            }
        return None
    
    def get_columns(self, obj):
        """Get all columns for this board"""
        # Order by position to maintain consistent column order
        columns = obj.columns.all().order_by('position')
        return ColumnSerializer(columns, many=True).data
    
    def get_action_items(self, obj):
        """Get all action items for the board"""
        action_items = obj.action_items.all().order_by('created_at')
        return ActionItemSerializer(action_items, many=True).data
    
    def get_current_voting_round(self, obj):
        """Get the active voting round"""
        active_round = obj.get_active_voting_round()
        return VotingRoundSerializer(active_round).data
    
    def get_is_facilitator(self, obj):
        """Check if current user is a facilitator of this board"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.is_facilitator(request.user)
        return False
    
    def get_facilitators(self, obj):
        """Get list of facilitators with user info"""
        facilitators = obj.facilitators.all().order_by('username')
        result = []
        for user in facilitators:
            # Calculate initials
            if user.first_name and user.last_name:
                initials = user.first_name[0] + user.last_name[0]
            else:
                initials = user.username[:2].upper()
            result.append({
                'id': user.id,
                'username': user.username,
                'initials': initials,
                'is_creator': user.id == obj.created_by_id
            })
        return result
    
    def get_can_edit_columns(self, obj):
        """Check if current user can edit columns"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_edit_columns(request.user)
        return False
    
    def get_can_edit_board_title(self, obj):
        """Check if current user can edit board title"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_edit_board_title(request.user)
        return False
    
    def get_can_delete_any_card(self, obj):
        """Check if current user can delete any card"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_delete_any_card(request.user)
        return False

class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for Tag - returns tag name and display label
    """
    display_name = serializers.CharField(source='get_name_display', read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'display_name']
        read_only_fields = ['id', 'name', 'display_name']

class VotingRoundSerializer(serializers.ModelSerializer):
    """
    Serializer for voting round - tracks voting rounds per board
    """

    class Meta:
        model = VotingRound
        fields = ['id', 'round_number', 'is_active', 'created_at']
        read_only_fields = ['id', 'round_number', 'is_active', 'created_at']


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
    tags = TagSerializer(many=True, read_only=True)  # for GET - returns full tag objects
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), 
        many=True, 
        write_only=True, 
        required=False,
        source='tags'
    )  # for POST/PATCH - accepts list of tag IDs

    class Meta:
        model = Card
        fields = ['id', 'column', 'retro_board', 'content', 'created_by', 'created_by_id', 'created_at', 'updated_at', 'position', 'is_anonymous', 'status', 'vote_count', 'user_vote_count', 'user_board_votes_remaining', 'color', 'tags', 'tag_ids']
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
        """Get number of times current user has voted on this card in the CURRENT round"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Get current active voting round
            current_round = obj.column.retro_board.get_active_voting_round() if obj.column else None
            if current_round:
                # Filter votes by current round only
                return obj.votes.filter(user=request.user, voting_round=current_round).count()
            else:
                # No active round - return 0 (voting not started or stopped)
                return 0
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

    def validate(self, data):
        """Check voting is open and user hasn't exceeded vote limits"""
        user = self.context['request'].user
        card = data['card']
        retro_board = card.column.retro_board

        # Check if voting has started
        active_round = retro_board.get_active_voting_round()
        if active_round is None:
            raise serializers.ValidationError(
                "Voting has not started yet. Wait for the facilitator to start voting."
            )

        # Check if user has reached total vote limit for THIS ROUND
        current_vote_count = user.get_board_vote_count(retro_board, voting_round=active_round)
        max_votes = retro_board.max_votes_per_round

        if current_vote_count >= max_votes:
            raise serializers.ValidationError(
                f"You have reached the maximum of {max_votes} votes for round {active_round.round_number}. "
                f"You currently have {current_vote_count} votes in this round." 
            )
        
        # Check per-card limit (if configured)
        if retro_board.max_votes_per_card is not None:
            user_votes_on_card = Vote.objects.filter(
                card=card,
                user=user,
                voting_round=active_round
            ).count()
            
            if user_votes_on_card >= retro_board.max_votes_per_card:
                raise serializers.ValidationError(
                    f"You have reached the maximum of {retro_board.max_votes_per_card} "
                    f"vote(s) on this card for round {active_round.round_number}."
                )
        
        return data

    def create(self, validated_data):
        # automatically set user to current user
        validated_data['user_id'] = self.context['request'].user.id
        # automatically assign vote to the boards current active round
        card = validated_data['card']
        board = card.column.retro_board
        validated_data['voting_round'] = board.get_active_voting_round()
        return super().create(validated_data)
    
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
    
class ActionItemSerializer(serializers.ModelSerializer):
    """
    Serializer for ActionItem with status tracking (todo, in_progress, completed)
    Read: returns full user objects for created_by and assignee
    Write: Accepts retro_board_id and content for creation, username for assignment
    """

    # GET - returns full user info - username, initials, avatar
    created_by = CustomUserSerializer(read_only=True)
    assignee = CustomUserSerializer(read_only=True)

    # POST - accepts board ID to create action item
    retro_board_id = serializers.IntegerField(write_only=True, required=False)

    # PATCH - accepts a username as a string to assign user to action item
    assignee_username = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = ActionItem
        fields = [
            'id',
            'retro_board',
            'retro_board_id',  # write only: for creating action items
            'content',
            'status',
            'created_by',
            'assignee',
            'assignee_username',  # write only: assigning by username
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'retro_board',
            'created_by',
            'created_at',
            'updated_at'
        ]

    def create(self, validated_data):
        """Create action item with current user as creator"""
        # Handle retro_board_id -> retro_board conversion
        retro_board_id = validated_data.pop('retro_board_id', None)
        if retro_board_id:
            validated_data['retro_board_id'] = retro_board_id
        
        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Handle assignee_username -> assignee lookup"""
        assignee_username = validated_data.pop('assignee_username', None)
        # Remove retro_board_id if passed (shouldn't change after creation)
        validated_data.pop('retro_board_id', None)

        if assignee_username is not None:
            if assignee_username:
                try:
                    instance.assignee = User.objects.get(username=assignee_username)
                except User.DoesNotExist:
                    raise serializers.ValidationError({
                        'assignee_username': f"User '{assignee_username}' not found"
                    })
            else:
                instance.assignee = None
        
        return super().update(instance, validated_data)