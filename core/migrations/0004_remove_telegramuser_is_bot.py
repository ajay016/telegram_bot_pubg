# Generated by Django 5.2.1 on 2025-05-24 17:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_paymentmethod_uid'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='telegramuser',
            name='is_bot',
        ),
    ]
