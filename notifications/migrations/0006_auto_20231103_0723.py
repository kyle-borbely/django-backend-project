# Generated by Django 2.2.28 on 2023-11-03 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_auto_20231014_1154'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationhistory',
            name='notification_name',
            field=models.CharField(max_length=200),
        ),
    ]
