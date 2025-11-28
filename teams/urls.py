# 🔗 TEAMS URL ROUTING - Simpler Router Configuration
# ==================================================
# Teams app has fewer models but more complex custom actions
# This demonstrates a cleaner router setup with focused endpoints

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 🎯 FOCUSED API DESIGN
# ====================
# Teams app only needs 2 main resources but with rich functionality:
# 
# /api/teams/ endpoints:
# - Standard CRUD for team management
# - Custom actions for member management
# - Board assignment actions
# - User-specific team filtering
# 
# /api/memberships/ endpoints:
# - Read-only access to membership records
# - Audit trail for who joined when
# - Filtering by team or user

router = DefaultRouter()

# TEAM MANAGEMENT
# =================
# Full CRUD + custom member management actions
router.register(r'teams', views.TeamViewSet)

# MEMBERSHIP AUDIT
# ==================  
# Read-only ViewSet for membership history/audit trail
# Useful for "when did user X join team Y?" queries
router.register(r'memberships', views.TeamMembershipViewSet)

# CLEAN URL INCLUSION
# ======================
# All team-related endpoints available under /api/teams/ prefix
urlpatterns = [
    path('', include(router.urls)),
]