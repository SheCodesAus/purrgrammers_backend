# Django REST Framework imports for API serialization
from rest_framework import serializers
# Django authentication imports
from django.contrib.auth import get_user_model, authenticate
# Import our custom models
from .models import UserProfile

# DJANGO SERIALIZERS EXPLAINED:
# Serializers convert between complex data types (like Django models) and native Python
# data types that can be easily rendered into JSON, XML, or other formats.
# They also handle deserialization (parsing JSON back to Django models).
#
# KEY CONCEPTS:
# 1. ModelSerializer: automatically generates fields from model
# 2. Serializer: manual field definition, more control
# 3. Validation: clean and validate data before saving
# 4. Context: pass request data to serializers for user-specific logic

# get_user_model(): Django best practice for getting User model
# Works with custom user models (like our CustomUser)
User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data - handles bio, location, and timestamps
    
    MODELSERIALIZER BENEFITS:
    - Automatically generates fields from model definition
    - Handles create() and update() operations automatically
    - Reduces code duplication
    - Maintains consistency with model field types and validation
    
    API USAGE:
    - GET: return profile data to frontend
    - PUT/PATCH: update profile information
    - Includes user info (id, username, initials) for convenience
    """
    
    # Include user fields for convenience (read-only)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    initials = serializers.CharField(source='user.initials', read_only=True)
    
    class Meta:
        """
        Meta class defines serializer configuration
        
        DJANGO PATTERN: Meta class
        - Common pattern in Django for model/serializer configuration
        - Keeps configuration separate from behavior
        - Provides clean, declarative syntax
        """
        model = UserProfile  # Which model this serializer handles
        
        # fields: specify which model fields to include in API
        # These become JSON keys in API responses
        fields = ['user_id', 'username', 'first_name', 'last_name', 'initials', 'bio', 'location', 'created_at', 'updated_at']
        
        # read_only_fields: can be read but not written via API
        # Protects timestamp fields from being manually set
        # Django handles these automatically (auto_now_add, auto_now)
        read_only_fields = ['created_at', 'updated_at']

class SimpleTeamSerializer(serializers.Serializer):
    """
    Simplified team serializer to avoid circular imports
    
    CIRCULAR IMPORT PROBLEM:
    - users.serializers imports teams.serializers
    - teams.serializers imports users.serializers
    - Python can't resolve this circular dependency
    
    SOLUTION: Simple Serializer
    - Use basic Serializer instead of ModelSerializer
    - Manually define only needed fields
    - Breaks circular dependency while providing team data
    
    SERIALIZER vs MODELSERIALIZER:
    - Serializer: manual field definition, more control
    - ModelSerializer: automatic from model, less code
    - Use Serializer when you need custom logic or to avoid imports
    """
    # Manual field definitions for team data
    # These fields must match the data structure passed to this serializer
    id = serializers.IntegerField()                    # Team ID
    name = serializers.CharField()                     # Team name
    description = serializers.CharField()              # Team description
    created_at = serializers.DateTimeField()          # When team was created

class CustomUserSerializer(serializers.ModelSerializer):
    """
    Main user serializer for API responses - includes profile, teams, and initials
    
    PURPOSE:
    - Read-only serializer for returning user data
    - Includes related data (profile, teams) in single API call
    - Used after login/registration to send complete user info
    
    PERFORMANCE CONSIDERATIONS:
    - SerializerMethodField makes database queries
    - Consider using select_related() and prefetch_related() in views
    - Balance between data completeness and API performance
    """
    
    # ReadOnlyField: includes model property in API response
    # initials property is defined in CustomUser model (@property)
    # Automatically calculated, never written via API
    initials = serializers.ReadOnlyField()  # Includes the initials property for frontend avatars
    
    # Nested serializer: includes full profile data in user response
    # read_only=True: profile data comes from separate profile endpoints
    # This gives frontend all profile info without separate API call
    profile = UserProfileSerializer(read_only=True)
    
    # SerializerMethodField: calls a method to get the value
    # Method name: get_teams() (get_ + field_name)
    # Allows complex logic for field calculation
    teams = serializers.SerializerMethodField()

    class Meta:
        model = User  # Our CustomUser model
        
        # FIELD SELECTION STRATEGY:
        # Include: data needed by frontend for user display and functionality
        # Exclude: sensitive data (password, email for privacy)
        # Include: calculated fields (initials) and related data (profile, teams)
        fields = ['id', 'username', 'first_name', 'last_name', 'initials', 'created_at', 'profile', 'teams']
        
        # READ-ONLY PROTECTION:
        # id: auto-generated primary key, never user-settable
        # created_at: timestamp set by Django, should never be modified
        read_only_fields = ['id', 'created_at']
    
    def get_teams(self, obj):
        """
        Get teams user is a member of - implements SerializerMethodField
        
        SERIALIZERMETHODFIELD PATTERN:
        - Method name must be get_<field_name>
        - obj parameter is the model instance being serialized
        - Return value becomes the field value in API response
        
        DJANGO ORM CONCEPTS:
        - obj.teams: ManyToMany relationship from User to Team
        - filter(): add WHERE clause to query
        - is_active=True: only show active teams (soft delete pattern)
        
        PERFORMANCE NOTE:
        - This makes a database query for each user
        - In list views, consider using prefetch_related('teams')
        - Or use a separate endpoint for user teams
        """
        # Get user's teams that are still active (not soft-deleted)
        teams = obj.teams.filter(is_active=True)
        # Use simple serializer to avoid circular imports
        return SimpleTeamSerializer(teams, many=True).data

# SEPARATION OF CONCERNS: Dedicated Registration Serializer
# Why separate from CustomUserSerializer?
# 1. Different fields: registration needs password, read operations don't
# 2. Different validation: password confirmation only needed on registration
# 3. Security: write operations should be more restrictive than read
# 4. Maintainability: easier to test and modify registration logic separately

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with password confirmation
    
    SECURITY CONSIDERATIONS:
    - Passwords are write-only (never returned in API responses)
    - Password confirmation prevents typos
    - Validation ensures passwords match before user creation
    
    FORM VALIDATION PATTERN:
    - Individual field validation: validate_<field_name>()
    - Cross-field validation: validate() method
    - Django calls these automatically during is_valid()
    """
    
    # write_only=True: field is required for input but never in output
    # Prevents passwords from being returned in API responses
    # Critical security practice for sensitive data
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        # REGISTRATION FIELDS:
        # Required: username, email (for login), password + confirmation
        # Optional: first_name, last_name (for better UX and initials)
        # Note: password_confirm is not a model field, just for validation
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, data):
        """
        Cross-field validation for registration data
        
        DJANGO VALIDATION LIFECYCLE:
        1. Field-level validation (validate_<field_name> methods)
        2. Object-level validation (this validate method)
        3. Model validation (model.clean() if defined)
        4. Database constraints
        
        VALIDATION BEST PRACTICES:
        - Validate early and often
        - Provide clear error messages
        - Use ValidationError for user-facing errors
        - Check business rules before database operations
        
        Args:
            data (dict): All validated field data
        
        Returns:
            dict: Validated data (can be modified)
        
        Raises:
            ValidationError: If validation fails
        """
        # Check that passwords match - basic form validation
        if data['password'] != data['password_confirm']:
            # ValidationError automatically returns 400 Bad Request
            # Message shows in API response for frontend to display
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def create(self, validated_data):
        """
        Create user with validated data - override default ModelSerializer behavior
        
        WHY OVERRIDE CREATE?
        - Remove password_confirm (not a model field)
        - Use create_user() instead of create() for proper password hashing
        - Handle any custom user creation logic
        
        DJANGO USER CREATION:
        - create_user(): built-in method that properly hashes passwords
        - create(): would store password in plain text (security risk!)
        - Always use create_user() for user models
        
        SECURITY NOTE:
        - Django automatically hashes passwords when using create_user()
        - Never store passwords in plain text
        - Password hashing is one-way (can't be decoded)
        
        Args:
            validated_data (dict): Clean data from validation
        
        Returns:
            User: Created user instance
        """
        # Remove password_confirm since it's not a model field
        # pop() removes and returns the value
        validated_data.pop('password_confirm')

        # TODO: Add password strength validation
        # - Minimum length requirements
        # - Character complexity requirements
        # - Common password checking
        # Use create_user() for proper password hashing
        user = User.objects.create_user(**validated_data)
        return user

class EmailOrUsernameLoginSerializer(serializers.Serializer): 
    """
    Serializer for flexible login (email OR username) with password
    
    WHY SERIALIZER INSTEAD OF MODELSERIALIZER?
    - Not creating/updating a model instance
    - Just validating credentials for authentication
    - Need custom validation logic for email/username flexibility
    
    AUTHENTICATION FLOW:
    1. User submits username/email + password
    2. Serializer validates format
    3. authenticate() checks credentials against database
    4. View generates and returns auth token
    
    BUSINESS REQUIREMENT:
    - Users can login with either email OR username
    - Improves user experience (don't need to remember which they used)
    - Requires custom authentication backend
    """
    
    # CharField: accepts any string value
    # Can be either username or email - validated in authenticate()
    username = serializers.CharField()  # accepts a string that can be either username or email
    
    # Password field with special styling for forms
    # style={'input_type': 'password'}: renders as password field in browsable API
    password = serializers.CharField(style={'input_type': 'password'})  # renders as password field

    def validate(self, attrs):
        """
        Validate login credentials using Django's authentication system
        
        DJANGO AUTHENTICATION:
        - authenticate(): checks credentials against all configured backends
        - Returns User object if credentials valid, None if invalid
        - Supports multiple authentication backends (our custom + default)
        
        AUTHENTICATION BACKENDS:
        - Default: username + password
        - Our custom: email OR username + password
        - Configured in settings.AUTHENTICATION_BACKENDS
        
        SECURITY CONSIDERATIONS:
        - Don't reveal whether username or email exists
        - Use same error message for all authentication failures
        - Check is_active to prevent disabled accounts from logging in
        
        Args:
            attrs (dict): Raw field data (username, password)
        
        Returns:
            dict: Validated data with user object added
        
        Raises:
            ValidationError: If authentication fails
        """
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            # Django's authenticate() function:
            # - Tries all configured authentication backends
            # - Our EmailOrUsernameModelBackend handles email/username logic
            # - Returns User object if credentials valid, None otherwise
            user = authenticate(
                request=self.context.get('request'),  # Pass request context
                username=username,  # Can be email or username
                password=password
            )

            if not user:
                # SECURITY: Don't reveal whether username/email exists
                # Same error message for all authentication failures
                raise serializers.ValidationError(
                    'Unable to login with provided credentials',
                    code='authorization'
                )
            
            if not user.is_active:
                # Check if account is disabled/deactivated
                # is_active=False prevents login without deleting account
                raise serializers.ValidationError(
                    'User account is disabled',
                    code='authorization'
                )
            
            # Add user object to validated data for use in view
            attrs['user'] = user
            return attrs
        else:
            # Both username and password are required
            raise serializers.ValidationError(
                'Must include "username" and "password".',
                code='authorization'
            )

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Enhanced UserProfile serializer with team information for profile pages
    
    NOTE: This is a second UserProfileSerializer (name collision)
    - First one (above) is basic profile data
    - This one includes team information for profile pages
    - Consider renaming to UserProfileWithTeamsSerializer for clarity
    
    DESIGN PATTERN: Different serializers for different use cases
    - List views: minimal data for performance
    - Detail views: complete data for full functionality
    - Update views: only editable fields
    """
    
    # SerializerMethodField for complex team data
    # This makes an additional database query - consider performance implications
    teams = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        # Include team information in profile response
        fields = ['bio', 'location', 'created_at', 'updated_at', 'teams']
        # Teams are read-only (managed via separate team endpoints)
        read_only_fields = ['created_at', 'updated_at', 'teams']

    def get_teams(self, obj):
        """
        Get team information for user's profile page
        
        PERFORMANCE OPTIMIZATION:
        - Use values() for dictionary output instead of model instances
        - Only include needed fields (id, name, description)
        - Faster than full model serialization
        
        ORM OPTIMIZATION:
        - obj.user.teams: traverse OneToOne relationship to User, then ManyToMany to teams
        - filter(is_active=True): only show active teams
        - values(): returns dictionaries instead of model instances (faster)
        
        Returns:
            list: List of team dictionaries with basic team info
        """
        # Get active teams for the profile's user
        # values() returns list of dictionaries (more efficient than model instances)
        return obj.user.teams.filter(is_active=True).values('id', 'name', 'description')