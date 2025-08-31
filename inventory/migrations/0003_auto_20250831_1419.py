from django.db import migrations
import random

def populate_user_ids(apps, schema_editor):
    """Generate unique 5-digit IDs for existing users"""
    User = apps.get_model('inventory', 'User')
    used_ids = set()
    
    for user in User.objects.all():
        if not user.user_id:  # Only assign if user_id is None
            while True:
                user_id = str(random.randint(10000, 99999))
                if user_id not in used_ids:
                    used_ids.add(user_id)
                    user.user_id = user_id
                    user.save()
                    break

def reverse_populate_user_ids(apps, schema_editor):
    """Remove user IDs (for rollback)"""
    User = apps.get_model('inventory', 'User')
    User.objects.all().update(user_id=None)

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0002_user_user_id'),  # This should match the migration that adds the user_id field
    ]

    operations = [
        migrations.RunPython(populate_user_ids, reverse_populate_user_ids),
    ]