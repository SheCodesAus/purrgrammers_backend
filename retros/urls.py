# URL ROUTING - Django REST Framework Router Pattern
# ====================================================
# DRF routers automatically generate URL patterns for ViewSets
# This eliminates the need to manually write each CRUD endpoint

from django.urls import path, include
from rest_framework.routers import DefaultRouter  # Auto-generates RESTful URL patterns
from . import views

# DRF ROUTER - Automatic URL Generation
# =======================================
# DefaultRouter creates standard REST endpoints for each registered ViewSet:
# 
# For 'retro-boards' -> RetroBoardViewSet:
# - GET    /api/retro-boards/           -> list all boards
# - POST   /api/retro-boards/           -> create new board
# - GET    /api/retro-boards/{id}/      -> retrieve specific board
# - PUT    /api/retro-boards/{id}/      -> update entire board
# - PATCH  /api/retro-boards/{id}/      -> partial update board
# - DELETE /api/retro-boards/{id}/      -> delete board
# 
# PLUS any @action decorated methods become custom endpoints:
# - GET /api/retro-boards/{id}/columns/ -> custom action
# - GET /api/retro-boards/{id}/vote_summary/ -> custom action

router = DefaultRouter()

# VIEWSET REGISTRATION
# ======================
# router.register(url_prefix, ViewSetClass)
# Each registration creates a full set of RESTful endpoints

router.register(r'retro-boards', views.RetroBoardViewSet)  # Main board management
router.register(r'columns', views.ColumnViewSet)          # Column CRUD operations  
router.register(r'cards', views.CardViewSet)              # Card management + voting
router.register(r'votes', views.VoteViewSet)              # Vote tracking
router.register(r'comments', views.CommentViewSet)        # Comment system
router.register(r'action-items', views.ActionItemViewSet) # action item

# URL INCLUSION
# ===============
# Include all router-generated URLs under the retros/ prefix
# Main urls.py will include this as: path('api/', include('retros.urls'))
urlpatterns = [
    path('', include(router.urls)),  # Includes ALL generated REST endpoints
]