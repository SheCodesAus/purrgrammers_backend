from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
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


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the current user's profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Get the profile for the authenticated user"""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def update(self, request, *args, **kwargs):
        """Update profile and return updated user data"""
        response = super().update(request, *args, **kwargs)
        
        # Return full user data including updated profile
        user_serializer = CustomUserSerializer(request.user)
        return Response({
            'user': user_serializer.data,
            'message': 'Profile updated successfully'
        })


class CurrentUserView(generics.RetrieveAPIView):
    """Get current user's full data (including profile and teams)"""
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
