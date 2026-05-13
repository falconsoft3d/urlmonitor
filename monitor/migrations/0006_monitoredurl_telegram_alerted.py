from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0005_siteconfig_registration_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitoredurl',
            name='telegram_alerted',
            field=models.BooleanField(default=False, verbose_name='Alerta Telegram enviada'),
        ),
    ]
