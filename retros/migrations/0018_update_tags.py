# Generated manually to update tags to match TAG_CHOICES

from django.db import migrations


def update_tags(apps, schema_editor):
    """Update tags to match current TAG_CHOICES"""
    Tag = apps.get_model('retros', 'Tag')
    
    # Current TAG_CHOICES from models.py
    current_tags = [
        # languages
        'python',
        'javascript',
        'html',
        'css',
        # frameworks
        'django',
        'react',
        'git/github',
        'vscode',
        'deployment',
        # other
        'tools',
        'team_culture',
        'workload',
        'content',
        'networking',
        'mentors',
    ]
    
    # Add new tags
    for tag_name in current_tags:
        Tag.objects.get_or_create(name=tag_name)
    
    # Remove old tags that are no longer in choices
    # (only if they're not being used by any cards)
    old_tags = ['java', 'csharp', 'typescript', 'nodejs', 'angular', 'communication', 'custom']
    for tag_name in old_tags:
        Tag.objects.filter(name=tag_name, cards__isnull=True).delete()


def reverse_tags(apps, schema_editor):
    """Reverse migration"""
    pass  # No destructive reverse needed


class Migration(migrations.Migration):

    dependencies = [
        ('retros', '0017_retroboard_max_votes_per_card_and_more'),
    ]

    operations = [
        migrations.RunPython(update_tags, reverse_tags),
    ]
