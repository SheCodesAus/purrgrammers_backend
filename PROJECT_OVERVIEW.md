# Purrgrammers Backend - Project Overview

## 📋 Project Summary
A Django REST Framework backend for a retrospective collaboration tool that enables teams to conduct structured retrospective meetings with digital sticky notes, voting, and commenting functionality.

## 🛠 Technical Stack
- **Backend Framework**: Django 5.1 + Django REST Framework 3.15.2
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: Token-based authentication
- **Deployment**: Heroku (configured with Gunicorn + WhiteNoise)
- **Additional**: CORS headers for frontend integration

## 🏗 Architecture Overview

### Models & Database Design
- **User Management**: Custom user model extending Django's AbstractUser
- **Retrospective Structure**: Hierarchical data model
  - `RetroBoard` → `Column` → `Card` → `Vote`/`Comment`
- **Relationships**: Foreign keys with proper cascading and related names
- **Constraints**: Unique constraints for data integrity (one vote per user per card)

### API Design Patterns
- **ViewSets**: Used for full CRUD operations (RetroBoardViewSet, ColumnViewSet, etc.)
- **Generic Views**: Used for authentication endpoints (UserRegistrationView)
- **Custom Actions**: `@action` decorators for specialized endpoints (voting, card retrieval)
- **Serializers**: Separate serializers for read/write operations

## 🔐 Authentication System

### Features Implemented
- **Flexible Login**: Email OR username authentication
- **Custom Backend**: `EmailOrUsernameModelBackend` for dual login support
- **Token Authentication**: Automatic token generation on registration/login
- **User Registration**: Complete signup flow with validation

### Security Measures
- Password confirmation validation
- Unique email/username constraints
- Token-based API security
- CORS configuration for frontend integration

## 📊 Key Features

### Retrospective Management
- Create and manage retrospective boards
- Customizable columns (Start/Stop/Keep/More/Less/Custom)
- Drag-and-drop positioning system
- Board lifecycle management (active/inactive)

### Interactive Elements
- **Cards**: Create, edit, and position sticky notes
- **Voting**: One vote per user per card with validation
- **Comments**: Thread-based discussions on cards
- **Anonymous Posting**: Optional anonymity for sensitive feedback

### User Experience
- Real-time collaboration ready
- Hierarchical data access (boards → columns → cards)
- Vote counting and user voting status
- User avatar generation with initials

## 🔧 Technical Implementation Details

### Database Optimization
- **Ordering**: Default ordering on models for consistent data retrieval
- **Related Names**: Proper reverse relationship naming
- **Constraints**: Database-level unique constraints for data integrity
- **Indexes**: Position-based ordering for UI drag-and-drop

### API Design
- **RESTful Endpoints**: Standard HTTP methods for resource management
- **Nested Resources**: Related data access (e.g., `/boards/{id}/columns/`)
- **Custom Actions**: Specialized endpoints for business logic
- **Error Handling**: Proper HTTP status codes and error responses

### Serialization Strategy
- **Read/Write Separation**: Different serializers for input/output
- **Computed Fields**: Vote counts, user voting status
- **Related Data**: Full user objects vs. ID-only fields
- **Context Passing**: Request context for user-specific data

## 📱 Frontend Integration Ready

### CORS Configuration
- Configured for cross-origin requests
- Ready for React/Vue/Angular frontend

### API Documentation
- Comprehensive endpoint documentation
- Clear request/response formats
- Authentication flow documentation

## 🚀 Deployment Configuration

### Production Ready
- **Heroku Deployment**: Configured with Procfile
- **Static Files**: WhiteNoise for static file serving
- **Environment Variables**: Secure configuration management
- **Database**: PostgreSQL production configuration
- **Requirements**: Pinned dependency versions

### Development Workflow
- **Migrations**: Proper Django migration management
- **Admin Interface**: Comprehensive admin configuration
- **Management Commands**: Custom commands for development tools

## 🎯 Business Logic Highlights

### Voting System
```python
# Prevents duplicate votes with database constraints
class Meta:
    unique_together = ['card', 'user']
```

### Flexible Authentication
```python
# Supports both email and username login
user = User.objects.get(
    Q(username__iexact=username) | Q(email__iexact=username)
)
```

### Position Management
```python
# Ensures proper ordering for drag-and-drop UIs
class Meta:
    ordering = ['position', 'created_at']
    unique_together = ['column', 'position']
```

## 💡 Key Design Decisions

1. **ViewSets vs. Views**: Used ViewSets for standard CRUD, Views for custom auth logic
2. **Token Auth**: Chose token over session auth for stateless API design
3. **Custom User Model**: Extended AbstractUser for future flexibility
4. **Hierarchical Data**: Structured data model for complex UI requirements
5. **Anonymous Support**: Built-in anonymity for sensitive retrospective feedback

## 🔍 Code Quality Features

- **Type Hints**: Clear parameter and return types
- **Documentation**: Comprehensive docstrings and comments
- **Error Handling**: Proper exception handling and user feedback
- **Validation**: Multi-level validation (serializer + database)
- **Testing Ready**: Structure supports comprehensive test coverage

## 🎨 Extensibility

The architecture supports easy extension for:
- Real-time features (WebSocket integration)
- File attachments on cards
- Team/workspace management
- Advanced voting systems
- Integration with external tools

---

*This project demonstrates proficiency in Django/DRF, API design, database modeling, authentication systems, and production deployment practices.*