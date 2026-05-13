from django.db import migrations


def copy_user_to_users(apps, schema_editor):
    MonitoredURL = apps.get_model('monitor', 'MonitoredURL')
    for url in MonitoredURL.objects.all():
        if url.user_id:
            url.users.add(url.user_id)


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0007_add_users_m2m'),
    ]

    operations = [
        migrations.RunPython(copy_user_to_users, migrations.RunPython.noop),
    ]
