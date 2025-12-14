# Data migration to add existing board creators to facilitators

from django.db import migrations


def populate_facilitators(apps, schema_editor):
    """Add each board's creator to its facilitators list"""
    RetroBoard = apps.get_model('retros', 'RetroBoard')
    for board in RetroBoard.objects.all():
        if board.created_by:
            board.facilitators.add(board.created_by)


def reverse_populate(apps, schema_editor):
    """Reverse: clear all facilitators (use with caution)"""
    # We don't actually want to remove all facilitators on reverse
    # Just pass - the schema migration will handle the field removal
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('retros', '0020_retroboard_facilitators_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_facilitators, reverse_populate),
    ]
