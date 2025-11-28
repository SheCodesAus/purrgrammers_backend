# Django authentication imports
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q  # For complex database queries

# DJANGO AUTHENTICATION BACKENDS EXPLAINED:
# Django supports multiple authentication backends for flexible login systems
# Default: username + password authentication only
# Custom: can authenticate with email, social media, LDAP, etc.
#
# AUTHENTICATION BACKEND WORKFLOW:
# 1. User submits credentials (username/email + password)
# 2. Django tries each backend in AUTHENTICATION_BACKENDS setting order
# 3. First backend that returns User object is used
# 4. If all backends return None, authentication fails
#
# WHY CUSTOM BACKEND?
# - Allow login with email OR username (better UX)
# - Maintain Django's security best practices
# - Support existing username-based users
# - Flexible authentication without changing User model

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either
    their username or email address with their password
    
    INHERITANCE FROM MODELBACKEND:
    - ModelBackend: Django's default authentication backend
    - Inherits permission checking methods (has_perm, etc.)
    - Only need to override authenticate() method
    - Maintains compatibility with Django's auth system
    
    BUSINESS REQUIREMENTS:
    - Users forget whether they used username or email to register
    - Improve user experience by accepting either
    - Maintain security by still requiring correct password
    - Case-insensitive matching for better usability
    
    SECURITY CONSIDERATIONS:
    - Still requires correct password validation
    - Timing attack protection (always hash password even if user not found)
    - Account status checking (is_active, user_can_authenticate)
    - No information leakage about valid usernames/emails
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with username OR email + password
        
        AUTHENTICATION FLOW:
        1. Extract username from request (could be username or email)
        2. Try to find user by username OR email (case-insensitive)
        3. Verify password against found user
        4. Check if user is allowed to authenticate
        5. Return User object if successful, None if failed
        
        PARAMETERS:
        - request: HTTP request object (for logging, IP tracking, etc.)
        - username: string that could be username OR email
        - password: plain text password to verify
        - **kwargs: additional auth parameters
        
        RETURNS:
        - User object: if authentication successful
        - None: if authentication failed
        
        SECURITY MEASURES:
        - Always run password hasher even on invalid username (timing attack protection)
        - Case-insensitive username/email lookup
        - Account status validation
        """
        # Handle different parameter names for flexibility
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)  # Default to model's USERNAME_FIELD

        # Basic validation - both username and password required
        if username is None or password is None:
            return None
        
        try:
            # DATABASE QUERY WITH Q OBJECTS:
            # Q objects allow complex queries with OR, AND, NOT operations
            # iexact: case-insensitive exact match
            # Q(username__iexact=username) | Q(email__iexact=username): username OR email match
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except User.DoesNotExist:
            # TIMING ATTACK PROTECTION:
            # Run password hasher even when user not found
            # Prevents attackers from timing differences to enumerate valid usernames
            User().set_password(password)
            return None
            
        # AUTHENTICATION VERIFICATION:
        # check_password(): secure password verification (handles hashing)
        # user_can_authenticate(): checks is_active and other account status
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None