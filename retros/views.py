# RETROS VIEWS - Complex ViewSet Patterns & Custom Actions

# - ModelViewSet for full CRUD operations
# - Custom @action decorators for specific endpoints
# - Permission handling and authentication
# - Complex logic (voting system)
# - Error handling and user feedback
# - Cross-model operations and relationships

# IMPORTS - DRF Core Components
# ===============================
from rest_framework import viewsets, permissions, status  # Core DRF classes
from rest_framework.decorators import action             # Custom endpoint decorator
from rest_framework.response import Response             # JSON response wrapper
from django.contrib.auth import get_user_model          # Dynamic user model reference
from .models import RetroBoard, Column, Card, Vote, Comment, ActionItem, Tag, VotingRound
from .serializers import (
    RetroBoardSerializer,
    ColumnSerializer,
    CardSerializer,
    VoteSerializer,
    CommentSerializer,
    ActionItemSerializer,
    TagSerializer,
    VotingRoundSerializer
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

# get_user_model() returns the active user model
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
    
    PLUS custom @action methods for specific operations
    
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
        user = self.request.user
        return RetroBoard.objects.filter(
            team__members=user  # returns only boards that user is a member of
        ).distinct().order_by('-created_at')
    
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

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """
        Generate a report for this board.
        
        GET /api/retro-boards/{id}/report/          → JSON report
        GET /api/retro-boards/{id}/report/?format=csv → CSV download
        
        Includes:
        - Tag summary (cards per tag)
        - Top voted cards
        - User engagement (anonymized)
        - Action items summary
        """
        from django.http import HttpResponse
        from django.db.models import Count
        import csv
        
        board = self.get_object()
        
        # Get all cards for this board
        cards = Card.objects.filter(
            column__retro_board=board
        ).prefetch_related('tags', 'votes')
        
        # TAG SUMMARY: Count cards per tag
        tag_summary = []
        for tag in Tag.objects.all():
            card_count = cards.filter(tags=tag).count()
            if card_count > 0:
                tag_summary.append({
                    'tag': tag.name,
                    'card_count': card_count
                })
        tag_summary.sort(key=lambda x: x['card_count'], reverse=True)
        
        # TOP VOTED CARDS: Cards with most votes
        top_voted = cards.annotate(
            total_votes=Count('votes')
        ).filter(total_votes__gt=0).order_by('-total_votes')[:10]
        
        top_voted_list = [{
            'content': card.content[:100],
            'votes': card.total_votes,
            'column': card.column.title if card.column else 'No column',
            'tags': [t.name for t in card.tags.all()]
        } for card in top_voted]
        
        # USER ENGAGEMENT: Anonymized stats
        # Get unique users who created cards or voted
        card_creators = cards.values('created_by').annotate(
            cards_created=Count('id')
        ).order_by('-cards_created')
        
        vote_casters = Vote.objects.filter(
            card__column__retro_board=board
        ).values('user').annotate(
            votes_cast=Count('id')
        ).order_by('-votes_cast')
        
        # Build anonymized user stats
        user_ids = set()
        for c in card_creators:
            if c['created_by']:
                user_ids.add(c['created_by'])
        for v in vote_casters:
            if v['user']:
                user_ids.add(v['user'])
        
        # Create anonymous mapping
        user_map = {uid: f"User {i+1}" for i, uid in enumerate(sorted(user_ids))}
        
        user_engagement = []
        for uid in user_ids:
            cards_created = next((c['cards_created'] for c in card_creators if c['created_by'] == uid), 0)
            votes_cast = next((v['votes_cast'] for v in vote_casters if v['user'] == uid), 0)
            user_engagement.append({
                'user': user_map[uid],
                'cards_created': cards_created,
                'votes_cast': votes_cast
            })
        user_engagement.sort(key=lambda x: x['cards_created'] + x['votes_cast'], reverse=True)
        
        # ACTION ITEMS SUMMARY
        action_items = ActionItem.objects.filter(retro_board=board)
        action_summary = {
            'total': action_items.count(),
            'todo': action_items.filter(status='todo').count(),
            'in_progress': action_items.filter(status='in_progress').count(),
            'completed': action_items.filter(status='completed').count(),
            'items': [{
                'content': item.content,
                'status': item.status,
                'assignee': item.assignee.username if item.assignee else 'Unassigned'
            } for item in action_items]
        }
        
        # BOARD SUMMARY
        board_summary = {
            'title': board.title,
            'total_cards': cards.count(),
            'total_votes': Vote.objects.filter(card__column__retro_board=board).count(),
            'total_participants': len(user_ids),
            'columns': [{
                'title': col.title,
                'card_count': cards.filter(column=col).count()
            } for col in board.columns.all()]
        }
        
        report_data = {
            'board_summary': board_summary,
            'tag_summary': tag_summary,
            'top_voted_cards': top_voted_list,
            'user_engagement': user_engagement,
            'action_items': action_summary
        }
        
        # CSV EXPORT
        if request.query_params.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="board_{board.id}_report.csv"'
            
            writer = csv.writer(response)
            
            # Board Summary
            writer.writerow(['BOARD SUMMARY'])
            writer.writerow(['Title', board_summary['title']])
            writer.writerow(['Total Cards', board_summary['total_cards']])
            writer.writerow(['Total Votes', board_summary['total_votes']])
            writer.writerow(['Total Participants', board_summary['total_participants']])
            writer.writerow([])
            
            # Columns
            writer.writerow(['COLUMNS'])
            writer.writerow(['Column', 'Card Count'])
            for col in board_summary['columns']:
                writer.writerow([col['title'], col['card_count']])
            writer.writerow([])
            
            # Tag Summary
            writer.writerow(['TAG SUMMARY'])
            writer.writerow(['Tag', 'Card Count'])
            for tag in tag_summary:
                writer.writerow([tag['tag'], tag['card_count']])
            writer.writerow([])
            
            # Top Voted Cards
            writer.writerow(['TOP VOTED CARDS'])
            writer.writerow(['Content', 'Votes', 'Column', 'Tags'])
            for card in top_voted_list:
                writer.writerow([card['content'], card['votes'], card['column'], ', '.join(card['tags'])])
            writer.writerow([])
            
            # User Engagement
            writer.writerow(['USER ENGAGEMENT (Anonymized)'])
            writer.writerow(['User', 'Cards Created', 'Votes Cast'])
            for user in user_engagement:
                writer.writerow([user['user'], user['cards_created'], user['votes_cast']])
            writer.writerow([])
            
            # Action Items
            writer.writerow(['ACTION ITEMS'])
            writer.writerow(['Status Summary:', f"To Do: {action_summary['todo']}", f"In Progress: {action_summary['in_progress']}", f"Completed: {action_summary['completed']}"])
            writer.writerow(['Content', 'Status', 'Assignee'])
            for item in action_summary['items']:
                writer.writerow([item['content'], item['status'], item['assignee']])
            
            return response
        
        return Response(report_data)

    @action(detail=True, methods=['post'])
    def start_voting(self, request, pk=None):
        """
        Start or advance voting for this board.
        - If no rounds exist: creates Round 1
        - If active round exists: deactivates it and creates next round
        - If stopped round exists: creates next round after highest
        - All users get fresh votes each round
        
        POST /api/retro-boards/{id}/start_voting/
        """
        board = self.get_object()
        
        # Permission check: only facilitators can start voting
        if not board.is_facilitator(request.user):
            return Response({
                'error': 'Only facilitators can start voting'
            }, status=status.HTTP_403_FORBIDDEN)
        
        current_round = board.get_active_voting_round()
        
        if current_round is not None:
            # Active round exists - deactivate it and start next
            current_round.is_active = False
            current_round.save()
            next_round_number = current_round.round_number + 1
            previous_round = current_round.round_number
        else:
            # No active round - check if any rounds exist (stopped state)
            last_round = board.voting_rounds.order_by('-round_number').first()
            if last_round:
                # Rounds exist but none active (stopped state) - start next round
                next_round_number = last_round.round_number + 1
                previous_round = last_round.round_number
            else:
                # No rounds at all - start Round 1
                next_round_number = 1
                previous_round = None
        
        new_round = VotingRound.objects.create(
            retro_board=board,
            round_number=next_round_number,
            is_active=True
        )
        
        if next_round_number == 1:
            message = 'Voting has started!'
        else:
            message = f'Voting round {new_round.round_number} started'
        
        # Broadcast to all connected clients
        try:
            broadcast_to_board(
                board.id,
                'voting_round_started',
                {
                    'previous_round': previous_round,
                    'current_voting_round': VotingRoundSerializer(new_round).data,
                    'message': message
                }
            )
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")
        
        return Response({
            'message': message,
            'current_voting_round': VotingRoundSerializer(new_round).data
        })
    
    @action(detail=True, methods=['post'])
    def reset_voting(self, request, pk=None):
        board = self.get_object()
        
        # Permission check: only facilitators can reset voting
        if not board.is_facilitator(request.user):
            return Response({
                'error': 'Only facilitators can reset voting'
            }, status=status.HTTP_403_FORBIDDEN)

        # delete all votes for board: vote -> card -> column -> retroboard
        Vote.objects.filter(card__column__retro_board=board).delete()

        # delete all voting rounds for board
        board.voting_rounds.all().delete()

        # Broadcast to all connected clients
        try:
            broadcast_to_board(
                board.id,
                'voting_reset',
                {
                    'message': 'Voting has been reset',
                    'current_voting_round': None
                }
            )
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")

        return Response({
            'message': 'Voting has been reset',
            'current_voting_round': None
        })

    @action(detail=True, methods=['post'])
    def stop_voting(self, request, pk=None):
        """
        Stop/pause voting for this board.
        - Deactivates the current round (votes are preserved)
        - Users cannot vote until a new round is started
        
        POST /api/retro-boards/{id}/stop_voting/
        """
        board = self.get_object()
        
        # Permission check: only facilitators can stop voting
        if not board.is_facilitator(request.user):
            return Response({
                'error': 'Only facilitators can stop voting'
            }, status=status.HTTP_403_FORBIDDEN)
        
        current_round = board.get_active_voting_round()

        if current_round is None:
            return Response({
                'error': 'No active voting round to stop',
                'current_voting_round': None
            }, status=status.HTTP_400_BAD_REQUEST)

        # Deactivate the current round (keep votes)
        current_round.is_active = False
        current_round.save()

        # Broadcast to all connected clients
        try:
            broadcast_to_board(
                board.id,
                'voting_stopped',
                {
                    'message': f'Voting round {current_round.round_number} has ended',
                    'stopped_round': current_round.round_number,
                    'current_voting_round': None
                }
            )
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")

        return Response({
            'message': f'Voting round {current_round.round_number} has ended',
            'stopped_round': current_round.round_number,
            'current_voting_round': None
        })
    
    def update(self, request, *args, **kwargs):
        """
        Override update to check permissions for different fields:
        - Title: requires can_edit_board_title permission
        - Voting settings & permission toggles: requires facilitator
        """
        board = self.get_object()
        user = request.user
        
        # Fields that require facilitator access
        facilitator_only_fields = [
            'max_votes_per_round',
            'max_votes_per_card',
            'participants_can_edit_columns',
            'participants_can_edit_board_title',
            'participants_can_delete_any_card',
        ]
        
        # Check if trying to update facilitator-only fields
        for field in facilitator_only_fields:
            if field in request.data:
                if not board.is_facilitator(user):
                    return Response({
                        'error': f'Only facilitators can change {field}'
                    }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if trying to update title
        if 'title' in request.data:
            if not board.can_edit_board_title(user):
                return Response({
                    'error': 'You do not have permission to edit the board title'
                }, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Only facilitators can delete boards"""
        board = self.get_object()
        if not board.is_facilitator(request.user):
            return Response({
                'error': 'Only facilitators can delete this board'
            }, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
    
    # websocket override - only need patch
    def perform_update(self, serializer):
        board = serializer.save()
        broadcast_to_board(
          board.id,
          'board_updated',
          RetroBoardSerializer(board, context={'request': self.request}).data  
        )
    
    @action(detail=True, methods=['post'])
    def add_facilitator(self, request, pk=None):
        """
        Add a user as facilitator to this board.
        Only existing facilitators can add new facilitators.
        User must be a team member.
        
        POST /api/retro-boards/{id}/add_facilitator/
        Body: { "user_id": 123 }
        """
        board = self.get_object()
        
        # Permission check: only facilitators can add facilitators
        if not board.is_facilitator(request.user):
            return Response({
                'error': 'Only facilitators can add other facilitators'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_to_add = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is a team member (if board has a team)
        if board.team and not board.team.members.filter(id=user_id).exists():
            return Response({
                'error': 'User must be a team member to be a facilitator'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already a facilitator
        if board.facilitators.filter(id=user_id).exists():
            return Response({
                'error': 'User is already a facilitator'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        board.facilitators.add(user_to_add)
        
        facilitators_data = RetroBoardSerializer(board, context={'request': request}).data['facilitators']
        
        # Broadcast facilitator change to all connected clients
        try:
            broadcast_to_board(
                board.id,
                'facilitators_updated',
                {
                    'action': 'added',
                    'user': {'id': user_to_add.id, 'username': user_to_add.username},
                    'facilitators': facilitators_data
                }
            )
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")
        
        return Response({
            'message': f'{user_to_add.username} is now a facilitator',
            'facilitators': facilitators_data
        })
    
    @action(detail=True, methods=['post'])
    def remove_facilitator(self, request, pk=None):
        """
        Remove a facilitator from this board.
        Only existing facilitators can remove facilitators.
        Cannot remove the board creator.
        
        POST /api/retro-boards/{id}/remove_facilitator/
        Body: { "user_id": 123 }
        """
        board = self.get_object()
        
        # Permission check: only facilitators can remove facilitators
        if not board.is_facilitator(request.user):
            return Response({
                'error': 'Only facilitators can remove facilitators'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({
                'error': 'user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cannot remove the creator
        if user_id == board.created_by_id:
            return Response({
                'error': 'Cannot remove the board creator as facilitator'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_to_remove = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is a facilitator
        if not board.facilitators.filter(id=user_id).exists():
            return Response({
                'error': 'User is not a facilitator'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        board.facilitators.remove(user_to_remove)
        
        facilitators_data = RetroBoardSerializer(board, context={'request': request}).data['facilitators']
        
        # Broadcast facilitator change to all connected clients
        try:
            broadcast_to_board(
                board.id,
                'facilitators_updated',
                {
                    'action': 'removed',
                    'user': {'id': user_to_remove.id, 'username': user_to_remove.username},
                    'facilitators': facilitators_data
                }
            )
        except Exception as e:
            print(f"WebSocket broadcast failed: {e}")
        
        return Response({
            'message': f'{user_to_remove.username} is no longer a facilitator',
            'facilitators': facilitators_data
        })
    
# COLUMN MANAGEMENT - Ordered Content ViewSet
# ==============================================
class ColumnViewSet(viewsets.ModelViewSet):
    """
    COLUMN MANAGEMENT VIEWSET
    """

    queryset = Column.objects.all()                        # Base queryset
    serializer_class = ColumnSerializer                    # Serialization handling
    permission_classes = [permissions.IsAuthenticated]    # Auth required

    def get_queryset(self):
        """POSITION-BASED ORDERING"""
        return Column.objects.all().order_by('position')
    
    def _check_column_permission(self, board, user):
        """Check if user can edit columns on this board"""
        if not board.can_edit_columns(user):
            return Response({
                'error': 'You do not have permission to edit columns on this board'
            }, status=status.HTTP_403_FORBIDDEN)
        return None
    
    def create(self, request, *args, **kwargs):
        """Check permission before creating column"""
        board_id = request.data.get('retro_board')
        if board_id:
            from .models import RetroBoard
            try:
                board = RetroBoard.objects.get(id=board_id)
                error_response = self._check_column_permission(board, request.user)
                if error_response:
                    return error_response
            except RetroBoard.DoesNotExist:
                pass  # Let the serializer handle the invalid board_id
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Check permission before updating column"""
        column = self.get_object()
        error_response = self._check_column_permission(column.retro_board, request.user)
        if error_response:
            return error_response
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Check permission before deleting column"""
        column = self.get_object()
        error_response = self._check_column_permission(column.retro_board, request.user)
        if error_response:
            return error_response
        return super().destroy(request, *args, **kwargs)
    
    # RELATIONSHIP ACTION: Get Column Cards
  
    @action(detail=True, methods=['get'])
    def cards(self, request, pk=None):
        """
        COLUMN CARD ACCESS ACTION
        """
        column = self.get_object()
        
        # REVERSE RELATIONSHIP ACCESS
        
        # Access cards through ForeignKey reverse relationship
        cards = column.cards.all()  # Uses related_name from Card.column field
        
        # CONTEXT FOR USER-SPECIFIC DATA
        
        # Pass request context for voting information
        serializer = CardSerializer(cards, many=True, context={'request': request})
        return Response(serializer.data)
    
    # WEB SOCKET OVERRIDES

    def perform_create(self, serializer):
        column = serializer.save()
        broadcast_to_board(
            column.retro_board.id,
            'column_created',
            ColumnSerializer(column).data
        )

    def perform_update(self, serializer):
        column = serializer.save()
        broadcast_to_board(
            column.retro_board.id,
            'column_updated',
            ColumnSerializer(column).data
        )

    def perform_destroy(self, instance):
        board_id = instance.retro_board.id
        column_id = instance.id
        instance.delete()
        broadcast_to_board(
            board_id,
            'column_deleted',
            {'id': column_id}
        )
    
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

    def destroy(self, request, *args, **kwargs):
        """
        Check permission before deleting card:
        - Own cards: always allowed
        - Others' cards: requires can_delete_any_card permission
        """
        card = self.get_object()
        user = request.user
        
        # Users can always delete their own cards
        if card.created_by_id != user.id:
            # Trying to delete someone else's card
            board = card.retro_board or (card.column.retro_board if card.column else None)
            if board and not board.can_delete_any_card(user):
                return Response({
                    'error': 'You do not have permission to delete cards created by others'
                }, status=status.HTTP_403_FORBIDDEN)
        
        return super().destroy(request, *args, **kwargs)

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
                
                # Broadcast vote to all users viewing the board
                board_id = card.column.retro_board.id
                broadcast_to_board(board_id, 'card_voted', {
                    'id': card.id,
                    'vote_count': card.vote_count
                })
                
                # REAL-TIME FEEDBACK
                remaining_votes = request.user.get_remaining_board_votes(card.column.retro_board)
                active_round = card.column.retro_board.get_active_voting_round()
                user_votes_on_card = card.votes.filter(user=request.user, voting_round=active_round).count()
                return Response({
                    'message': 'Vote added',
                    'remaining_votes': remaining_votes,
                    'total_card_votes': card.vote_count,
                    'user_votes_on_card': user_votes_on_card
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
                
                # Broadcast vote removal to all users viewing the board
                board_id = card.column.retro_board.id
                broadcast_to_board(board_id, 'card_voted', {
                    'id': card.id,
                    'vote_count': card.vote_count
                })
                
                # REAL-TIME FEEDBACK
                remaining_votes = request.user.get_remaining_board_votes(card.column.retro_board)
                active_round = card.column.retro_board.get_active_voting_round()
                user_votes_on_card = card.votes.filter(user=request.user, voting_round=active_round).count() if active_round else 0
                
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

class ActionItemViewSet(viewsets.ModelViewSet):
    """
    ACTION ITEM MANAGEMENT
    
    Endpoints:
    - GET    /api/action-items/           → List all (filtered by board)
    - POST   /api/action-items/           → Create new action item
    - GET    /api/action-items/{id}/      → Get specific action item
    - PATCH  /api/action-items/{id}/      → Update status/assignee
    - DELETE /api/action-items/{id}/      → Delete action item
    """
    
    queryset = ActionItem.objects.all()
    serializer_class = ActionItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter by board if provided"""
        queryset = ActionItem.objects.all().order_by('created_at')
        board_id = self.request.query_params.get('board_id')
        if board_id:
            queryset = queryset.filter(retro_board_id=board_id)
        return queryset
    
    def perform_create(self, serializer):
        """Create action item and broadcast via WebSocket"""
        action_item = serializer.save()
        broadcast_to_board(
            action_item.retro_board.id,
            'action_item_created',
            ActionItemSerializer(action_item).data
        )
    
    def perform_update(self, serializer):
        action_item = serializer.save()
        broadcast_to_board(
            action_item.retro_board.id,
            'action_item_updated',
            ActionItemSerializer(action_item).data
        )
    
    def perform_destroy(self, instance):
        board_id = instance.retro_board.id
        action_item_id = instance.id
        instance.delete()
        broadcast_to_board(
            board_id,
            'action_item_deleted',
            {'id': action_item_id}
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for Tags
    
    Tags are predefined and seeded via migration.
    Frontend can fetch all available tags to display in a dropdown/selector.
    
    Endpoints:
    - GET /api/tags/        → List all available tags
    - GET /api/tags/{id}/   → Get specific tag
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]