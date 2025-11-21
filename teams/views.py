from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Team, TeamMembership
from .serializers import (
    TeamSerializer,
    TeamListSerializer,
    TeamMembershipSerializer,
    TeamMembershipCreateSerializer
)

User = get_user_model()

class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teams
    Supports full CRUD operations plus custom actions for member management
    """
    queryset = Team.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return TeamListSerializer
        return TeamSerializer
    
    def get_queryset(self):
        """Filter teams based on user preferences or access"""
        queryset = Team.objects.filter(is_active=True)
        
        # optional: filter by teams user is member of with query param
        if self.request.query_params.get('my_teams'):
            queryset = queryset.filter(members=self.request.user)
        
        return queryset.select_related('created_by').prefetch_related('members', 'memberships__user')
    
    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """Add a member to the team"""
        team = self.get_object()
        
        # prepare data with team_id
        data = request.data.copy()
        data['team_id'] = team.id
        
        serializer = TeamMembershipCreateSerializer(
            data=data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            membership = serializer.save()
            return Response({
                'message': 'Member added successfully',
                'membership': TeamMembershipSerializer(membership).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='remove-member/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """Remove a member from the team"""
        team = self.get_object()
        
        try:
            user_to_remove = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            membership = TeamMembership.objects.get(team=team, user=user_to_remove)
            membership.delete()
            return Response({
                'message': f'{user_to_remove.username} removed from {team.name}'
            }, status=status.HTTP_200_OK)
        
        except TeamMembership.DoesNotExist:
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
    
    @action(detail=True, methods=['get'], url_path='retro-boards')
    def retro_boards(self, request, pk=None):
        """Get all retro boards assigned to this team"""
        team = self.get_object()
        
        # import here to avoid circular imports
        from retros.serializers import RetroBoardSerializer
        
        boards = team.retro_boards.all()
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
            board.assigned_teams.add(team)
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
            board.assigned_teams.remove(team)
            return Response({
                'message': f'Board "{board.title}" unassigned from team "{team.name}"'
            }, status=status.HTTP_200_OK)
        
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

class TeamMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for viewing team memberships
    Useful for audit trails and membership history
    """
    queryset = TeamMembership.objects.all()
    serializer_class = TeamMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter memberships based on query parameters"""
        queryset = TeamMembership.objects.all().select_related('user', 'team', 'added_by')
        
        # filter by team
        team_id = self.request.query_params.get('team')
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        
        # filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset
