from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0004_monitoredurl_is_public_monitoredurl_public_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfig',
            name='registration_enabled',
            field=models.BooleanField(default=True, verbose_name='Registro de nuevos usuarios activo'),
        ),
    ]
