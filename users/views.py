# Django REST Framework imports for API views and responses
from rest_framework import generics, permissions, status
from rest_framework.views import APIView  
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
# Django authentication imports
from django.contrib.auth import get_user_model
# Our custom serializers and models
from .serializers import UserRegistrationSerializer, CustomUserSerializer, EmailOrUsernameLoginSerializer, UserProfileSerializer, UserProfileWithTeamsSerializer
from .models import UserProfile

# DJANGO REST FRAMEWORK CONCEPTS:
# - generics: Pre-built view classes for common patterns (CreateAPIView, etc.)
# - permissions: Control who can access endpoints
# - status: HTTP status codes (201 Created, 400 Bad Request, etc.)
# - APIView: Base class for custom API views
# - Response: DRF wrapper for HTTP responses (auto-handles JSON)

# AUTHENTICATION STRATEGY:
# - Token authentication: stateless, good for APIs
# - Each user gets a unique token after login
# - Frontend sends token in Authorization header
# - No sessions needed (unlike Django's default auth)

User = get_user_model()

# API DESIGN DECISION: Generic Views vs ViewSets
# We're using generic views for user authentication endpoints because:
# 1. More explicit about what each endpoint does
# 2. Easier to customize for specific authentication requirements
# 3. Follows standard Django patterns for auth
# 4. Registration and login are special cases, not standard CRUD
#
# ViewSets are better for:
# - Standard CRUD operations (Create, Read, Update, Delete)
# - Resource management (teams, retro boards, cards)
# - When you need all REST endpoints for a model
#
# Generic Views are better for:
# - Custom business logic endpoints
# - Authentication flows
# - Single-purpose endpoints
# - When you only need 1-2 HTTP methods

class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint with automatic login (returns token + user data)
    
    CREATEAPIVIEW PATTERN:
    - Handles POST requests for creating new resources
    - Automatically uses serializer for validation and creation
    - Returns 201 Created on success, 400 Bad Request on validation errors
    - We override create() method for custom post-registration logic
    
    BUSINESS LOGIC:
    - Register new user account
    - Immediately log them in (auto-generate token)
    - Return both user data and auth token
    - Frontend can store token and redirect to dashboard
    
    SECURITY CONSIDERATIONS:
    - AllowAny permission (anyone can register)
    - Password validation in serializer
    - Email uniqueness enforced by model
    """
    queryset = User.objects.all()  # Required by CreateAPIView (though not directly used)
    serializer_class = UserRegistrationSerializer  # Which serializer to use for validation
    permission_classes = [permissions.AllowAny]  # Anyone can register (no authentication required)

    def create(self, request, *args, **kwargs):
        """
        Override create method to return token + user info after registration
        
        WHY OVERRIDE CREATE?
        - Default CreateAPIView only returns created object
        - We need to generate auth token immediately
        - Frontend needs both user data AND token for immediate login
        - Custom response format for better UX
        
        FLOW:
        1. Validate registration data using serializer
        2. Create new user account
        3. Generate authentication token
        4. Return user data + token for immediate login
        
        RESPONSE FORMAT:
        {
            "user": {user object with profile/teams},
            "token": "auth_token_string",
            "message": "success message"
        }
        
        Args:
            request: HTTP request object
            *args, **kwargs: Additional arguments from URL routing
        
        Returns:
            Response: JSON response with user data and auth token
        """
        try:
            # STEP 1: Validate and create user
            # get_serializer() uses self.serializer_class (UserRegistrationSerializer)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)  # Raises ValidationError if invalid
            user = serializer.save()  # Calls serializer.create(), returns User object
            
            # STEP 2: Generate authentication token
            # get_or_create(): returns (token, created) tuple
            # If token exists, use it; if not, create new one
            token, created = Token.objects.get_or_create(user=user)
            
            # STEP 3: Prepare user data for response
            # Use CustomUserSerializer for consistent user data format
            # Includes profile, teams, initials, etc.
            user_serializer = CustomUserSerializer(user)
            
            # STEP 4: Return combined response
            return Response({
                'user': user_serializer.data,     # Full user object
                'token': token.key,               # Authentication token
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # ERROR HANDLING:
            # Catch any unexpected errors during registration
            # Return user-friendly error message
            # Log actual error for debugging (in production, use proper logging)
            return Response(
                {'detail': f'Error creating user: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class CustomAuthToken(ObtainAuthToken):
    """
    Custom login endpoint that accepts email OR username and returns token + user data
    
    OBTAINAUTHTOKEN PATTERN:
    - Built-in DRF view for token authentication
    - Default only accepts username + password
    - We override to accept email OR username
    - We customize response to include user data
    
    WHY CUSTOM LOGIN VIEW?
    - Support email/username login flexibility
    - Return complete user data (not just token)
    - Frontend needs user info for immediate app state setup
    - Consistent response format across all auth endpoints
    
    AUTHENTICATION FLOW:
    1. User submits email/username + password
    2. Custom serializer validates credentials
    3. Generate or retrieve auth token
    4. Return token + complete user data
    """
    
    # Use our custom serializer instead of default
    # EmailOrUsernameLoginSerializer handles email/username flexibility
    serializer_class = EmailOrUsernameLoginSerializer

    def post(self, request, *args, **kwargs):
        """
        Handle login requests with custom response format
        
        AUTHENTICATION PROCESS:
        1. Validate credentials using custom serializer
        2. Get or create auth token for user
        3. Return token + complete user data
        
        WHY OVERRIDE POST?
        - Default ObtainAuthToken only returns token
        - We want to return user data too
        - Frontend needs immediate access to user info
        - Avoid additional API call after login
        
        TOKEN MANAGEMENT:
        - get_or_create(): reuse existing token if available
        - Tokens don't expire by default (consider adding expiration)
        - One token per user (revoke old when creating new)
        
        Args:
            request: HTTP request with username/email and password
        
        Returns:
            Response: JSON with token and user data
        """
        # Validate login credentials using our custom serializer
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)  # Raises ValidationError if invalid
        
        # Get validated user object from serializer
        user = serializer.validated_data['user']
        
        # Get or create authentication token
        # If user already has token, reuse it; otherwise create new one
        token, created = Token.objects.get_or_create(user=user)

        # Return token and complete user data using CustomUserSerializer
        # This gives frontend everything needed for immediate app setup
        user_serializer = CustomUserSerializer(user)
        return Response({
            'token': token.key,           # Authentication token for API calls
            'user': user_serializer.data  # Complete user data (profile, teams, etc.)
        })

class PublicUserProfileView(APIView):
    """
    View any user's profile (read-only)
    
    ENDPOINT: GET /api/users/profile/{user_id}/
    
    PURPOSE:
    - Allow logged-in users to view other users' profiles
    - Read-only access (no PATCH/PUT)
    - Useful for team member info, card author details, etc.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Get a specific user's profile by user_id"""
        try:
            user = CustomUser.objects.get(id=user_id)
            profile, created = UserProfile.objects.get_or_create(user=user)
            serializer = UserProfileWithTeamsSerializer(profile)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class UserProfileView(APIView):
    """
    User profile management endpoint - handles GET and PATCH requests
    
    APIVIEW PATTERN:
    - More flexible than generic views
    - Handle multiple HTTP methods in one class
    - Custom logic for each method type
    - Good for endpoints that don't fit standard CRUD patterns
    
    PROFILE MANAGEMENT:
    - GET: retrieve current user's profile
    - PATCH: update profile fields (partial updates)
    - Automatic profile creation if doesn't exist
    - Only authenticated users can access
    
    BUSINESS LOGIC:
    - Profiles are optional (created on demand)
    - Users can only access their own profile
    - Support partial updates (PATCH vs PUT)
    """
    permission_classes = [IsAuthenticated]  # Must be logged in to access profile
    
    def get(self, request):
        """
        Get current user's profile data
        
        GET_OR_CREATE PATTERN:
        - UserProfile is optional (not created during user registration)
        - Created automatically when first accessed
        - get_or_create() prevents race conditions
        
        AUTHENTICATION:
        - request.user: authenticated user from token
        - IsAuthenticated permission ensures user is logged in
        - No need to check if user is None
        
        RESPONSE FORMAT:
        Returns complete profile data including:
        - bio, location
        - created_at, updated_at timestamps
        - teams information (via SerializerMethodField)
        
        Returns:
            Response: JSON with profile data
        """
        # Get or create profile for current user
        # get_or_create() returns (object, created) tuple
        # If profile exists, returns it; if not, creates new one
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Serialize profile data for JSON response
        serializer = UserProfileWithTeamsSerializer(profile)
        return Response(serializer.data)
    
    def patch(self, request):
        """
        Update current user's profile (partial update)
        
        PATCH vs PUT:
        - PATCH: partial updates (only send changed fields)
        - PUT: full replacement (send all fields)
        - PATCH is more user-friendly for forms
        
        PARTIAL UPDATE FLOW:
        1. Get or create user's profile
        2. Validate submitted data (only changed fields)
        3. Update and save profile
        4. Return updated profile data
        
        VALIDATION:
        - partial=True: allows partial data validation
        - Only validates fields that are provided
        - Missing fields keep their current values
        
        ERROR HANDLING:
        - 400 Bad Request: validation errors
        - 200 OK: successful update
        
        Args:
            request: HTTP request with profile data to update
        
        Returns:
            Response: Updated profile data or validation errors
        """
        # Get or create profile for current user
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Create serializer with existing profile and new data
        # partial=True: allow partial updates (don't require all fields)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Save updated profile to database
            serializer.save()
            # Return updated profile data
            return Response(serializer.data)
        
        # Return validation errors as 400 Bad Request
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
