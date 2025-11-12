# NOTE: using mostly viewsets, but will use APIView if needed for custom behaviour or @actions
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action # lets us add custom routes for @actions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import RetroBoard, Column, Card, Vote, Comment
from .serializers import (
    RetroBoardSerializer,
    ColumnSerializer,
    CardSerializer,
    VoteSerializer,
    CommentSerializer
)

User = get_user_model()

class RetroBoardViewSet(viewsets.ModelViewSet): # automatically creates CRUD endpoints
    """
    ViewSet for managing RetroBoards
    Provides: list, create, retrieve, update, destroy
    Creates endpoints: GET, POST, PUT, DELETE for /api/retro-boards/
    """
    
    queryset = RetroBoard.objects.all()
    serializer_class = RetroBoardSerializer
    permission_classes = [permissions.IsAuthenticated] # Authentication enabled!
    
    def get_queryset(self):
        """Only return active boards, ordered by creation date"""
        return RetroBoard.objects.filter(is_active=True).order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def columns(self, request, pk=None):
        """Get all columns for a specific board"""
        board = self.get_object()
        columns = board.columns.all()
        serializer = ColumnSerializer(columns, many=True)
        return Response(serializer.data)
    
class ColumnViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing Columns
    Provides: list, create, retrieve, update, destroy
    """

    queryset = Column.objects.all() # queries the Column model
    serializer_class = ColumnSerializer # how to convert between Python objects and JSON
    permission_classes = [permissions.IsAuthenticated] # Authentication enabled!

    # overrides default behaviour and returns columns ordered by position
    def get_queryset(self):
        """Return columns ordered by position"""
        return Column.objects.all().order_by('position')
    
    # creates custom endpoint: /api/columns/5/cards/ to get all cards in a column
    @action(detail=True, methods=['get'])
    def cards(self, request, pk=None):
        """Get all cards for a specific column"""
        column = self.get_object()
        cards = column.cards.all() # uses the related_name from the Card model
        serializer = CardSerializer(cards, many=True, context={'request': request}) # sends request context to CardSerializer (needed for user has voted)
        return Response(serializer.data)
    
class CardViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing Cards
    Provides: list, create, retrieve, update, destroy
    Creates endpoints: GET, POST, PUT, DELETE for /api/cards/
    """

    queryset = Card.objects.all() # queries the Card model
    serializer_class = CardSerializer # convert between Python objects and JSON
    permission_classes = [permissions.IsAuthenticated] # Authentication enabled!

    def get_queryset(self):
        """Return Cards ordered by position within their column"""
        return Card.objects.all().order_by('position', '-created_at')
    
    def perform_create(self, serializer):
        """Automatically set the card creator to current user"""
        serializer.save(created_by=self.request.user)

    # creates endpoint for /api/cards/5/vote/ with the only method: POST
    @action(detail=True, methods=['post'])  
    def vote(self, request, pk=None):  
        """Vote on a card - creates new vote"""
        card = self.get_object() # gets the card (ID from URL)
        vote_data = {'card': card.id} # prepares data for serializer
        vote_serializer = VoteSerializer(data=vote_data, context={'request': request})
        if vote_serializer.is_valid():
            vote_serializer.save()
            return Response({'message': 'Vote added'}, status=status.HTTP_201_CREATED)
        return Response(vote_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='vote')  # Different URL path
    def remove_vote(self, request, pk=None):  # Different method name
        """Remove vote from a card"""
        card = self.get_object()
        try:
            vote = Vote.objects.get(user=request.user, card=card)
            vote.delete()
            return Response({'message': 'Vote removed'}, status=status.HTTP_204_NO_CONTENT)
        except Vote.DoesNotExist:
            return Response({'error': 'Vote not found'}, status=status.HTTP_404_NOT_FOUND)
    
class VoteViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing votes
    Provides: list, create, retrieve, update, destroy
    Creates endpoints: GET, POST, PUT, DELETE for /api/votes/
    """

    queryset = Vote.objects.all() # queries Vote model
    serializer_class = VoteSerializer # convert between Python and JSON
    permission_classes = [permissions.IsAuthenticated] # Authentication enabled!

    # overrides default ordering
    def get_queryset(self):
        """Return votes ordered by creation date - newest first"""
        return Vote.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        """Automatically set the voter to current user"""
        serializer.save(user=self.request.user)

class CommentViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing votes
    Provides: list, create, retrieve, update, destroy
    Creates endpoints: GET, POST, PUT, DELETE for /api/comments/
    """

    queryset = Comment.objects.all() # queries Comment model
    serializer_class = CommentSerializer # convert between Python and JSON
    permission_classes = [permissions.IsAuthenticated] # Authentication enabled!

    def get_queryset(self):
        """Return comments ordered by creatio date - oldest first"""
        return Comment.objects.all().order_by('created_at')
    
    def perform_create(self, serializer):
        """Automatically set the commenter to current user"""
        serializer.save(user=self.request.user)