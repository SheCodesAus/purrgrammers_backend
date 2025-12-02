from django.contrib import admin
from .models import RetroBoard, Column, Card, Vote, Comment, ActionItem

@admin.register(RetroBoard)
class RetroBoardAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at', 'created_by')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display = ('title', 'retro_board', 'column_type', 'position', 'color', 'created_at')
    list_filter = ('column_type', 'created_at', 'retro_board')
    search_fields = ('title', 'retro_board__title')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('retro_board', 'position')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('retro_board')

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('content_preview', 'column', 'created_by', 'position', 'vote_count', 'is_anonymous', 'created_at')
    list_filter = ('is_anonymous', 'created_at', 'column__retro_board', 'column__column_type')
    search_fields = ('content', 'column__title', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'vote_count')
    ordering = ('column', 'position')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('column', 'created_by', 'column__retro_board')

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'card_preview', 'created_at')
    list_filter = ('created_at', 'card__column__retro_board')
    search_fields = ('user__username', 'card__content')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def card_preview(self, obj):
        return obj.card.content[:30] + "..." if len(obj.card.content) > 30 else obj.card.content
    card_preview.short_description = 'Card'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'card', 'card__column')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'card_preview', 'content_preview', 'is_anonymous', 'created_at')
    list_filter = ('is_anonymous', 'created_at', 'card__column__retro_board')
    search_fields = ('content', 'user__username', 'card__content')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('created_at',)
    
    def content_preview(self, obj):
        return obj.content[:40] + "..." if len(obj.content) > 40 else obj.content
    content_preview.short_description = 'Comment'
    
    def card_preview(self, obj):
        return obj.card.content[:20] + "..." if len(obj.card.content) > 20 else obj.card.content
    card_preview.short_description = 'Card'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'card', 'card__column')

@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ('content_preview', 'retro_board', 'status', 'created_by', 'assignee', 'created_at')
    list_filter = ('status', 'created_at', 'retro_board')
    search_fields = ('content', 'retro_board__title', 'created_by__username', 'assignee__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('retro_board', 'created_by', 'assignee', 'original_column')