# Generated by Django 2.2.28 on 2023-08-17 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_name', models.CharField(max_length=50)),
                ('notification_text', models.TextField(max_length=400)),
                ('activate', models.CharField(max_length=20)),
                ('receiver', models.CharField(max_length=10)),
                ('date_time', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
