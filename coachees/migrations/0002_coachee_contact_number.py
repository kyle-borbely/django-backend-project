# Generated by Django 2.2.28 on 2023-04-21 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coachees', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='coachee',
            name='contact_number',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
