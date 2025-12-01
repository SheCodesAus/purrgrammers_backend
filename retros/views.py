# RETROS VIEWS - Complex ViewSet Patterns & Custom Actions

# - ModelViewSet for full CRUD operations
# - Custom @action decorators for business-specific endpoints
# - Permission handling and authentication
# - Complex business logic (voting system)
# - Error handling and user feedback
# - Cross-model operations and relationships

# IMPORTS - DRF Core Components
# ===============================
from rest_framework import viewsets, permissions, status  # Core DRF classes
from rest_framework.decorators import action             # Custom endpoint decorator
from rest_framework.response import Response             # JSON response wrapper
from django.contrib.auth import get_user_model          # Dynamic user model reference
from .models import RetroBoard, Column, Card, Vote, Comment
from .serializers import (
    RetroBoardSerializer,
    ColumnSerializer,
    CardSerializer,
    VoteSerializer,
    CommentSerializer
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_to_board(board_id, event_type, data):
    """
    Broadcast even to all websocket connections viewing the board

    Args:
    board_id: the id of the board
    event_type: 'card_created', 'card_updated', 'card_deleted', 'card_moved'
    data: dictionary of data to send
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'board_{board_id}',
        {
            'type': event_type,
            'data': data
        }
    )

# get_user_model() returns the active user model (could be custom)
# This is more flexible than importing a specific User model
User = get_user_model()

# RETRO BOARD MANAGEMENT - Main ViewSet

class RetroBoardViewSet(viewsets.ModelViewSet):
    """
    MAIN BOARD MANAGEMENT VIEWSET
    
    ModelViewSet provides these endpoints automatically:
    - GET    /api/retro-boards/       -> list() - all boards
    - POST   /api/retro-boards/       -> create() - new board
    - GET    /api/retro-boards/{id}/  -> retrieve() - specific board
    - PUT    /api/retro-boards/{id}/  -> update() - full update
    - PATCH  /api/retro-boards/{id}/  -> partial_update() - partial update
    - DELETE /api/retro-boards/{id}/  -> destroy() - delete board
    
    PLUS custom @action methods for business-specific operations
    
    WHY MODELVIEWSET?
    - Provides full CRUD automatically
    - Can override methods for custom behavior
    - Easy to add custom actions with @action decorator
    - Follows REST conventions out of the box
    """
    
    queryset = RetroBoard.objects.all()           # Base query (modified by get_queryset)
    serializer_class = RetroBoardSerializer       # How to serialize/deserialize data
    permission_classes = [permissions.IsAuthenticated]  # Must be logged in
    
    def get_queryset(self):
        """
        CUSTOM QUERY FILTERING
        Override to modify what data users can see
        Only return active boards, ordered by creation date
        
        PERFORMANCE NOTE: This runs for every request
        Consider adding select_related/prefetch_related for optimization
        """
        return RetroBoard.objects.filter(is_active=True).order_by('-created_at')
    
    # CUSTOM ACTION: Get Board Columns
    
    @action(detail=True, methods=['get'])  # Creates: GET /api/retro-boards/{id}/columns/
    def columns(self, request, pk=None):
        """
        RELATIONSHIP TRAVERSAL ACTION
        Get all columns for a specific board
        
        WHY CUSTOM ACTION?
        - More semantic than /api/columns/?board_id=X
        - Ensures proper board context and permissions
        - Can add board-specific column logic here
        
        URL PATTERN: /api/retro-boards/5/columns/
        """
        board = self.get_object()              # Get board from URL param (pk)
        columns = board.columns.all()         # Use reverse relationship
        serializer = ColumnSerializer(columns, many=True)  # Serialize queryset
        return Response(serializer.data)
    
    # CUSTOM ACTION: Voting Summary
    
    @action(detail=True, methods=['get'])  # Creates: GET /api/retro-boards/{id}/vote_summary/
    def vote_summary(self, request, pk=None):
        """
        BUSINESS LOGIC ACTION: Get voting summary for the board and current user
        
        COMPLEX BUSINESS RULES:
        - Each user gets maximum 5 votes per board
        - Need to track votes used vs remaining
        - Must handle unauthenticated users gracefully
        
        RETURNS: JSON with voting constraints and current status
        """
        board = self.get_object()
        user = request.user
        
        # SECURITY CHECK: Authentication Required
        
        if not user.is_authenticated:
            return Response({
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # BUSINESS LOGIC: Vote Counting
        
        return Response({
            'board_id': board.id,
            'board_title': board.title,
            'max_votes_per_user': 5,                                    
            'user_total_votes': board.get_user_vote_count(user),       
            'user_remaining_votes': board.get_user_remaining_votes(user), 
            'can_vote_more': user.can_vote_on_board(board)             
        })
    
    # CUSTOM ACTION: Card Pool Management
    @action(detail=True, methods=['get'])
    def card_pool(self, request, pk=None):
        """
        DRAFT CARD POOL ACCESS
        
        BUSINESS LOGIC:
        - Cards start in 'draft' status before being placed in columns
        - Card pool shows all unplaced cards for a retro board
        - Users can move cards from pool to columns via drag & drop
        
        QUERY FILTERING:
        - status='draft': Only unplaced cards
        - column__isnull=True: Not assigned to any column yet
        - retro_board=board: Scoped to current board
        
        URL PATTERN: GET /api/retro-boards/{id}/card-pool/
        """
        board = self.get_object()
        
        
        draft_cards = Card.objects.filter(
            retro_board=board,
            status='draft',
            column__isnull=True
        )
        
        # CONTEXT PASSING
        # ==================
        # Pass request context for user-specific data (voting status)
        serializer = CardSerializer(draft_cards, many=True, context={'request': request})
        return Response(serializer.data)
    
# COLUMN MANAGEMENT - Ordered Content ViewSet
# ==============================================
class ColumnViewSet(viewsets.ModelViewSet):
    """
    COLUMN MANAGEMENT VIEWSET
    
    BUSINESS PURPOSE:
    - Manages retro board columns (Start, Stop, Continue)
    - Maintains display order through position field
    - Provides card access through relationship
    
    MODELVIEWSET FEATURES:
    - Full CRUD operations for columns
    - Automatic REST endpoint generation
    - Custom ordering via get_queryset override
    - Relationship traversal with custom actions
    
    WHY SEPARATE FROM BOARDS?
    - Columns can be customized per board
    - Different retro formats may need different columns
    - Allows for drag & drop reordering
    """

    queryset = Column.objects.all()                        # Base queryset
    serializer_class = ColumnSerializer                    # Serialization handling
    permission_classes = [permissions.IsAuthenticated]    # Auth required

    def get_queryset(self):
        """
        POSITION-BASED ORDERING
        
        WHY OVERRIDE?
        - UI needs consistent left-to-right column order
        - position field determines visual layout
        - Ensures Start -> Stop -> Continue order
        
        BUSINESS RULE:
        - position=0: Leftmost column (usually 'Start')
        - position=1: Middle column (usually 'Stop') 
        - position=2: Rightmost column (usually 'Continue')
        """
        return Column.objects.all().order_by('position')
    
    # RELATIONSHIP ACTION: Get Column Cards
  
    @action(detail=True, methods=['get'])
    def cards(self, request, pk=None):
        """
        COLUMN CARD ACCESS ACTION
        
        RELATIONSHIP TRAVERSAL:
        - Uses reverse ForeignKey relationship
        - column.cards.all() accesses related Card objects
        - related_name='cards' defined in Card model
        
        CONTEXT IMPORTANCE:
        - CardSerializer needs request context
        - Required for user-specific voting information
        - Enables 'user_has_voted' SerializerMethodField
        
        URL PATTERN: GET /api/columns/{id}/cards/
        
        WHY NOT DIRECT QUERY?
        - Ensures proper column context and permissions
        - Can add column-specific card filtering later
        - More semantic than /api/cards/?column_id=X
        """
        column = self.get_object()
        
        # REVERSE RELATIONSHIP ACCESS
        
        # Access cards through ForeignKey reverse relationship
        cards = column.cards.all()  # Uses related_name from Card.column field
        
        # CONTEXT FOR USER-SPECIFIC DATA
        
        # Pass request context for voting information
        serializer = CardSerializer(cards, many=True, context={'request': request})
        return Response(serializer.data)
    
# CARD MANAGEMENT - Logic ViewSet  

class CardViewSet(viewsets.ModelViewSet):
    """
    CARD MANAGEMENT WITH VOTING SYSTEM
    
    This ViewSet demonstrates advanced patterns:
    - Custom create behavior (perform_create)
    - Complex business logic in custom actions
    - Error handling with detailed user feedback
    - State transitions (draft -> placed)
    - Vote counting and validation
    
    BUSINESS RULES:
    - Cards start in 'draft' status (in card pool)
    - Users can vote on cards (max 5 votes per board)
    - Cards can be moved between columns
    - Vote removal follows LIFO (Last In, First Out)
    """

    queryset = Card.objects.all()                           # Base queryset
    serializer_class = CardSerializer                       # Serialization class
    permission_classes = [permissions.IsAuthenticated]     # Authentication required

    def get_queryset(self):
        """
        OPTIMIZED QUERY ORDERING
        Return Cards ordered by position within their column, then by creation date
        This ensures consistent UI display order
        """
        return Card.objects.all().order_by('position', '-created_at')
    
    def perform_create(self, serializer):
        card = serializer.save(created_by=self.request.user)

        # broadcast to all users viewing board
        if card.retro_board:
            broadcast_to_board(
                card.retro_board.id,
                'card_created',
                CardSerializer(card).data
            )

    def perform_update(self, serializer):
        card = serializer.save()

        # broadcast to all users viewing board
        if card.retro_board:
            broadcast_to_board(
                card.retro_board.id,
                'card_updated',
                CardSerializer(card).data
            )

    def perform_destroy(self, instance):
        board_id = instance.retro_board.id if instance.retro_board else None
        card_id = instance.id

        instance.delete()

        # broadcast to all users viewing board
        if board_id:
            broadcast_to_board(
                board_id,
                'card_deleted',
                {'id': card_id}
            )

    # VOTING ACTION - Handles both POST (add vote) and DELETE (remove vote)
    # =====================================================================
    
    @action(detail=True, methods=['post', 'delete'])  # POST/DELETE /api/cards/{id}/vote/
    def vote(self, request, pk=None):
        """
        CARD VOTING SYSTEM
        
        POST - Add a vote:
        - Users can vote multiple times on same card
        - Maximum 5 votes per user per board (not per card)
        - Validates vote limits before creating vote
        
        DELETE - Remove a vote (LIFO pattern):
        - Users can remove their own votes only
        - Removes most recent vote if user voted multiple times
        - LIFO prevents gaming the system
        """
        card = self.get_object()
        
        if request.method == 'POST':
            # ADD VOTE
            # =========
            
            #  Vote Limit Check
            if not request.user.can_vote_on_board(card.column.retro_board):
                remaining = request.user.get_remaining_board_votes(card.column.retro_board)
                return Response({
                    'error': f'You have reached the maximum of 5 votes for this board. Remaining votes: {remaining}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # VOTE CREATION PROCESS
            vote_data = {'card': card.id}
            vote_serializer = VoteSerializer(data=vote_data, context={'request': request})
            
            if vote_serializer.is_valid():
                vote_serializer.save()  # VoteSerializer handles user assignment
                
                # REAL-TIME FEEDBACK
                remaining_votes = request.user.get_remaining_board_votes(card.column.retro_board)
                return Response({
                    'message': 'Vote added',
                    'remaining_votes': remaining_votes,
                    'total_card_votes': card.vote_count,
                    'user_votes_on_card': card.votes.filter(user=request.user).count()
                }, status=status.HTTP_201_CREATED)
            
            return Response(vote_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            # REMOVE VOTE (LIFO - Last In, First Out)
            # ========================================
            
            try:
                # Get the most recent vote from this user on this card
                vote = card.votes.filter(user=request.user).order_by('-created_at').first()
                
                if not vote:
                    return Response({
                        'error': 'No vote found to remove'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # VOTE DELETION
                vote.delete()
                
                # REAL-TIME FEEDBACK
                remaining_votes = request.user.get_remaining_board_votes(card.column.retro_board)
                user_votes_on_card = card.votes.filter(user=request.user).count()
                
                return Response({
                    'message': 'Vote removed',
                    'remaining_votes': remaining_votes,
                    'total_card_votes': card.vote_count,
                    'user_votes_on_card': user_votes_on_card
                }, status=status.HTTP_200_OK)
            
            except Exception as e:
                # UNEXPECTED ERROR HANDLING
                return Response({
                    'error': f'Error removing vote: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # STATE TRANSITION ACTION: Card Movement
    
    @action(detail=True, methods=['patch'])
    def move_to_column(self, request, pk=None):
        """
        CARD STATE MANAGEMENT & DRAG-DROP SUPPORT
        
        STATE TRANSITIONS:
        - draft → placed: Moving from card pool to column
        - placed → placed: Moving between columns
        - placed → draft: Moving back to pool
        
        BUSINESS LOGIC:
        - Cards maintain retro_board association always
        - column=None indicates card is in pool (draft status)
        - position determines order within column
        
        FRONTEND INTEGRATION:
        - Supports drag & drop UI interactions
        - Real-time position updates
        - Smooth state transitions
        
        URL PATTERN: PATCH /api/cards/{id}/move-to-column/
        PAYLOAD: {'column_id': 5, 'position': 2}
        """
        card = self.get_object()
        column_id = request.data.get('column_id')
        position = request.data.get('position', 0)  # Default to top position
        
        # STATE TRANSITION LOGIC
        
        if column_id:
            # MOVING TO COLUMN
            
            # Place card in specific column (draft → placed)
            column = Column.objects.get(id=column_id)
            card.column = column
            card.retro_board = column.retro_board  # Ensure board consistency
            card.status = 'placed'                  # Update status
        else:
            # MOVING TO POOL
            
            # Return card to pool (placed → draft)
            card.column = None
            card.status = 'draft'
            # Keep retro_board association when moving back to pool
        
        # POSITION UPDATE
        
        # Update display order within column/pool
        card.position = position
        card.save()
        
        # UPDATED RESPONSE
        # ==================
        # Return updated card data with new state
        return Response(CardSerializer(card, context={'request': request}).data)
    
# VOTE MANAGEMENT - Audit Trail ViewSet

class VoteViewSet(viewsets.ModelViewSet):
    """
    VOTE TRACKING & AUDIT VIEWSET
    
    PURPOSE:
    - Direct vote management (usually not needed by frontend)
    - Administrative access to voting data
    - Audit trail for voting behavior
    - Bulk operations if needed
    
    BUSINESS NOTE:
    - Most voting happens through CardViewSet.vote() action
    - This ViewSet provides lower-level access
    - Useful for analytics and administration
    
    ENDPOINTS PROVIDED:
    - GET /api/votes/ → All votes (admin view)
    - POST /api/votes/ → Direct vote creation
    - GET /api/votes/{id}/ → Specific vote details
    - DELETE /api/votes/{id}/ → Direct vote removal
    
    SECURITY CONSIDERATION:
    - Users should only access their own votes
    - Consider adding permission filtering
    """

    queryset = Vote.objects.all()                          # Base queryset
    serializer_class = VoteSerializer                      # Vote serialization
    permission_classes = [permissions.IsAuthenticated]    # Auth required

    def get_queryset(self):
        """
        CHRONOLOGICAL ORDERING
        
        WHY NEWEST FIRST?
        - Shows recent voting activity
        - Useful for audit trails
        - Matches user expectation for activity feeds
        
        POTENTIAL ENHANCEMENTS:
        - Filter by user: ?user=123
        - Filter by board: ?board=456
        - Filter by date range: ?from_date=2024-01-01
        """
        return Vote.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        """
        AUTOMATIC USER ASSIGNMENT
        
        SECURITY PATTERN:
        - Always use authenticated user as voter
        - Prevents vote impersonation
        - Maintains audit trail integrity
        
        DJANGO PATTERN:
        - perform_create() runs before save()
        - Allows modification of save behavior
        - Common pattern for setting user fields
        """
        serializer.save(user=self.request.user)

# COMMENT MANAGEMENT - Discussion ViewSet

class CommentViewSet(viewsets.ModelViewSet):
    """
    COMMENT SYSTEM VIEWSET
    
    PURPOSE:
    - Manages discussion/comments on retro cards
    - Enables team conversation and clarification
    - Provides threaded discussion capability
    
    BUSINESS VALUE:
    - Teams can discuss card content
    - Clarify ambiguous feedback
    - Add context to retro items
    - Build on each other's ideas
    
    ENDPOINTS PROVIDED:
    - GET /api/comments/ → All comments
    - POST /api/comments/ → Add new comment
    - GET /api/comments/{id}/ → Specific comment
    - PUT /api/comments/{id}/ → Edit comment
    - DELETE /api/comments/{id}/ → Remove comment
    
    ORDERING STRATEGY:
    - Oldest first for natural conversation flow
    - Matches chat/discussion expectations
    - Different from votes (newest first)
    """

    queryset = Comment.objects.all()                       # Base queryset
    serializer_class = CommentSerializer                   # Comment serialization  
    permission_classes = [permissions.IsAuthenticated]    # Auth required

    def get_queryset(self):
        """
        CONVERSATION FLOW ORDERING
        
        WHY OLDEST FIRST?
        - Natural conversation chronology
        - Users read comments in order they were posted
        - Makes follow-up comments make sense in context
        
        CONTRAST WITH VOTES:
        - Votes ordered newest first (activity feed style)
        - Comments ordered oldest first (conversation style)
        - Different UI patterns require different ordering
        
        FUTURE ENHANCEMENTS:
        - Threading/reply support
        - Filter by card: ?card=123
        - Pagination for long discussions
        """
        return Comment.objects.all().order_by('created_at')  # Chronological order
    
    def perform_create(self, serializer):
        """
        AUTOMATIC AUTHORSHIP ASSIGNMENT
        
        SECURITY & AUDIT:
        - Always use authenticated user as comment author
        - Prevents comment impersonation
        - Maintains discussion integrity
        
        BUSINESS LOGIC:
        - Comments are tied to specific users
        - Enables proper attribution in discussions
        - Supports moderation if needed
        
        DJANGO PATTERN:
        - perform_create() runs before save()
        - Standard pattern for user field assignment
        - Consistent with VoteViewSet approach
        """
        serializer.save(user=self.request.user)