# Django URL routing imports
from django.urls import path
# Import our custom views
from . import views

# DJANGO URL PATTERNS EXPLAINED:
# Django uses URL patterns to map HTTP requests to view functions/classes
# path() function creates URL pattern with name for reverse lookup
# Patterns are tried in order until match is found
#
# URL STRUCTURE:
# path('pattern/', ViewClass.as_view(), name='url_name')
# - pattern: URL to match (can include variables)
# - ViewClass.as_view(): converts class-based view to function
# - name: unique identifier for reverse URL lookup

# API ENDPOINT DESIGN PRINCIPLES:
# - RESTful conventions: POST for create, GET for read, etc.
# - Clear, descriptive URLs: /register/, /login/, /profile/
# - Consistent naming: use nouns for resources
# - Logical grouping: all user endpoints under /users/

# USER AUTHENTICATION ENDPOINTS:
# These endpoints handle user account creation, login, and profile management
# All endpoints return JSON responses for API consumption
urlpatterns = [
    # USER REGISTRATION: POST /api/users/register/
    # Creates new user account and returns auth token + user data
    # Permission: AllowAny (anyone can register)
    # Body: {username, email, first_name, last_name, password, password_confirm}
    # Response: {user: {...}, token: "...", message: "..."}
    path('register/', views.UserRegistrationView.as_view(), name='user_register'),
    
    # USER LOGIN: POST /api/users/login/
    # Authenticates user with email OR username + password
    # Permission: AllowAny (anyone can attempt login)
    # Body: {username: "email_or_username", password: "..."}
    # Response: {token: "...", user: {...}}
    path('login/', views.CustomAuthToken.as_view(), name='user_login'),
    
    # USER PROFILE: GET/PATCH /api/users/profile/
    # GET: retrieve current user's profile data
    # PATCH: update profile fields (bio, location)
    # Permission: IsAuthenticated (must be logged in)
    # GET Response: {bio: "...", location: "...", created_at: "...", teams: [...]}
    # PATCH Body: {bio: "...", location: "..."} (partial updates allowed)
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
]

# URL NAMING CONVENTIONS:
# - user_register: for reverse lookup in tests/templates
# - user_login: consistent with Django auth patterns
# - user_profile: clear indication of endpoint purpose
#
# REVERSE URL LOOKUP:
# In views/tests: reverse('user_register') returns '/api/users/register/'
# In templates: {% url 'user_login' %} generates login URL
#
# URL INCLUDES:
# These URLs are included in main urls.py as:
# path('api/users/', include('users.urls'))
# Final URLs become: /api/users/register/, /api/users/login/, etc.