from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

## router automatically creates all CRUD urls for the ViewSets
router = DefaultRouter()
router.register(r'retro-boards', views.RetroBoardViewSet)
router.register(r'columns', views.ColumnViewSet)
router.register(r'cards', views.CardViewSet)
router.register(r'votes', views.VoteViewSet)
router.register(r'comments', views.CommentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]