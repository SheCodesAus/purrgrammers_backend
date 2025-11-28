from rest_framework import generics, permissions, status
from rest_framework.views import APIView  
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import UserRegistrationSerializer, CustomUserSerializer, EmailOrUsernameLoginSerializer, UserProfileSerializer
from .models import UserProfile

User = get_user_model()

# we are not using viewsets in the users app as we are only handling registration and login.
# generic views are better because: more explicit about what the endpoint does, easier to customise, follows more standard django patterns for auth

class UserRegistrationView(generics.CreateAPIView):
    """Create a new user and return token + user data"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # Anyone can register

    def create(self, request, *args, **kwargs):
        """Override create to return token + user info after registration"""
        try:
            # Use the registration serializer to create user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()  # This returns the user object directly
            
            # Create token for auto-login
            token, created = Token.objects.get_or_create(user=user)
            
            # Return user data (using read serializer) + token
            user_serializer = CustomUserSerializer(user)
            
            return Response({
                'user': user_serializer.data,
                'token': token.key,
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'detail': f'Error creating user: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class CustomAuthToken(ObtainAuthToken):
    """Custom logon view that returns token and user info AND accepts email or username"""

    serializer_class = EmailOrUsernameLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        # return the token and user info using CustomUserSerializer

        user_serializer = CustomUserSerializer(user)
        return Response({
            'token': token.key,
            'user': user_serializer.data
        })
    
# we are using APIView on user profile, not viewset

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current users profile"""
        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    def patch(self, request):
        """Update profile"""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)