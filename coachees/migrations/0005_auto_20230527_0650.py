# Generated by Django 2.2.28 on 2023-05-27 10:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('coachees', '0004_coachingsession_engagementinfo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('call_type', models.CharField(choices=[('Chemistry Call', 'Chemistry Call'), ('Training', 'Training')], default='Chemistry Call', max_length=20)),
            ],
            options={
                'verbose_name': 'Session',
            },
        ),
        migrations.RemoveField(
            model_name='engagementinfo',
            name='coaching_status',
        ),
        migrations.RemoveField(
            model_name='engagementinfo',
            name='engagement_status',
        ),
        migrations.RemoveField(
            model_name='engagementinfo',
            name='num_sessions',
        ),
        migrations.AddField(
            model_name='coachee',
            name='coaching_status',
            field=models.CharField(choices=[('Assigned', 'Assigned'), ('Not Assigned', 'Not Assigned')], default='Not Assigned', max_length=30),
        ),
        migrations.AddField(
            model_name='coachee',
            name='engagement_status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Start Engagement', 'Start Engagement'), ('End Engagement', 'End Engagement')], default='Pending', max_length=30),
        ),
        migrations.AddField(
            model_name='coachee',
            name='num_sessions',
            field=models.IntegerField(default=0),
        ),
        migrations.DeleteModel(
            name='CoachingSession',
        ),
        migrations.AddField(
            model_name='session',
            name='engagement_info',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='coachees.EngagementInfo'),
        ),
    ]
