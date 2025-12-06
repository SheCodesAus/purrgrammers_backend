# TEAMS VIEWS - Advanced ViewSet Patterns & Member Management

# CORE IMPORTS
# ==============
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import Team, TeamMembership
from .serializers import (
    TeamSerializer,
    TeamListSerializer,                               # Lighter serializer for list view
    TeamMembershipSerializer,
    TeamMembershipCreateSerializer                    # Specialized create serializer
)
from retros.views import broadcast_to_board


# Always use get_user_model() instead of importing User directly
# This ensures compatibility with custom user models
User = get_user_model()

# TEAM MANAGEMENT - Advanced ViewSet Patterns
# ==============================================
class TeamViewSet(viewsets.ModelViewSet):
    
    
    queryset = Team.objects.filter(is_active=True)     # Only active teams
    permission_classes = [permissions.IsAuthenticated] # Must be logged in
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TeamListSerializer      # Lighter serializer for lists
        return TeamSerializer              # Full serializer for detail operations
    
    def get_queryset(self):
       
        
        queryset = Team.objects.filter(is_active=True, members=self.request.user)
        
        # PERFORMANCE OPTIMIZATION
        # =========================
        # Eager loading to prevent N+1 query problems
        return queryset.select_related('created_by').prefetch_related('members', 'memberships__user')
    
    # CUSTOM ACTION: Add Team Member
    # ================================
    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """
        MEMBER MANAGEMENT ACTION
        """
        team = self.get_object()
        
        # DATA PREPARATION
        # Add team context to request data for validation
        data = request.data.copy()
        data['team_id'] = team.id
        
        # Use create-specific serializer for different validation rules
        serializer = TeamMembershipCreateSerializer(
            data=data, 
            context={'request': request}  # Pass request for user context
        )
        
        if serializer.is_valid():
            membership = serializer.save()

            # broadcast to all boards using this team
            for board in team.retro_boards.all():
                broadcast_to_board(
                    board.id,
                    'team_updated',
                    {'team_id': team.id, 'action': 'member_added'}
                )
            return Response({
                'message': 'Member added successfully',
                'membership': TeamMembershipSerializer(membership).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # CUSTOM ACTION: Remove Team Member (Advanced URL Pattern)
    # ==========================================================
    @action(detail=True, methods=['delete'], url_path='remove-member/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """
        MEMBER REMOVAL WITH URL PARAMETERS
        
        """
        team = self.get_object()
        
    
        # Validate user exists before attempting removal
        try:
            user_to_remove = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        
        # Find and delete the specific membership relationship
        try:
            membership = TeamMembership.objects.get(team=team, user=user_to_remove)
            membership.delete()

            # broadcast to boards
            for board in team.retro_boards.all():
                broadcast_to_board(
                    board.id,
                    'team_updated',
                    {'team_id': team.id, 'action': 'member_removed'}
                )

            return Response({
                'message': f'{user_to_remove.username} removed from {team.name}'
            }, status=status.HTTP_200_OK)
            
        
        except TeamMembership.DoesNotExist:
            # BUSINESS LOGIC ERROR
            # =====================
            return Response(
                {'error': 'User is not a member of this team'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of a team with membership details"""
        team = self.get_object()
        memberships = team.memberships.all().select_related('user', 'added_by')
        serializer = TeamMembershipSerializer(memberships, many=True)
        return Response(serializer.data)
    
    # CROSS-APP INTEGRATION: Board Management
    # =========================================
    @action(detail=True, methods=['get'], url_path='retro-boards')
    def retro_boards(self, request, pk=None):
        """
        CROSS-APP RELATIONSHIP ACCESS
        
        URL: GET /api/teams/{id}/retro-boards/
        """
        team = self.get_object()
        
        # LAZY IMPORT PATTERN
        # =====================
        # Import only when needed to avoid circular dependencies
        from retros.serializers import RetroBoardSerializer
        
        boards = team.retro_boards.all()  # Many-to-many relationship
        serializer = RetroBoardSerializer(boards, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='assign-board')
    def assign_board(self, request, pk=None):
        """Assign a retro board to this team"""
        team = self.get_object()
        board_id = request.data.get('board_id')
        
        if not board_id:
            return Response(
                {'error': 'board_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # import here to avoid circular imports
        from retros.models import RetroBoard
        
        try:
            board = RetroBoard.objects.get(id=board_id)
            board.team = team
            board.save()
            return Response({
                'message': f'Board "{board.title}" assigned to team "{team.name}"'
            }, status=status.HTTP_200_OK)
        
        except RetroBoard.DoesNotExist:
            return Response(
                {'error': 'Board not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['delete'], url_path='unassign-board/(?P<board_id>[^/.]+)')
    def unassign_board(self, request, pk=None, board_id=None):
        """Remove board assignment from team"""
        team = self.get_object()
        
        # import here to avoid circular imports
        from retros.models import RetroBoard
        
        try:
            board = RetroBoard.objects.get(id=board_id)
            if board.team == team:
                board.team = None
                board.save()
                return Response({
                    'message': f'Board "{board.title}" unassigned from team "{team.name}"'
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Board is not assigned to this team'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except RetroBoard.DoesNotExist:
            return Response(
                {'error': 'Board not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], url_path='my-teams')
    def my_teams(self, request):
        """Get all teams the current user is a member of"""
        teams = Team.objects.filter(
            members=request.user, 
            is_active=True
        ).select_related('created_by').prefetch_related('members')
        
        serializer = TeamListSerializer(teams, many=True)
        return Response(serializer.data)

# AUDIT TRAIL VIEWSET - Read-Only Pattern
# =========================================
class TeamMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """
    AUDIT TRAIL MANAGEMENT VIEWSET
    
    READ-ONLY PATTERN:
    - Only provides list() and retrieve() endpoints
    - No create/update/delete operations
    - Perfect for historical data and audit trails
    
    BUSINESS USE CASES:
    - "When did user X join team Y?"
    - "Who added this user to the team?"
    - "What's the membership history?"
    - Compliance and audit requirements
    
    FILTERING CAPABILITIES:
    - ?team=5 -> memberships for specific team
    - ?user=123 -> teams that user belongs to
    - Combined filtering for specific relationships
    """
    
    queryset = TeamMembership.objects.all()
    serializer_class = TeamMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        🔍 FLEXIBLE FILTERING FOR AUDIT QUERIES
        
        QUERY OPTIMIZATION:
        - select_related for ForeignKey relationships
        - Reduces database queries for related objects
        
        FILTER PATTERNS:
        - Optional filtering via query parameters
        - Maintains flexibility without multiple endpoints
        - RESTful design with query-based filtering
        """
        # OPTIMIZED BASE QUERY
        # =====================
        queryset = TeamMembership.objects.all().select_related('user', 'team', 'added_by')
        
        # CONDITIONAL FILTERING
        # =======================
        # Filter by team: GET /api/memberships/?team=5
        team_id = self.request.query_params.get('team')
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        
        # Filter by user: GET /api/memberships/?user=123
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # FUTURE ENHANCEMENT IDEAS
        # =========================
        # - Date range filtering: ?from_date=2024-01-01&to_date=2024-12-31
        # - Role filtering: ?role=admin
        # - Active status filtering: ?active=true
        
        return queryset
