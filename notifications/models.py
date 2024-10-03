from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from django.contrib.postgres.fields import JSONField


# Create your models here.
class Notification(models.Model):
    """
    Notification which is created from admin pannel
    """

    notification_name = models.CharField(max_length=50)
    notification_text = models.TextField(max_length=400)
    activate = models.CharField(max_length=20)
    receiver = models.CharField(max_length=10)
    date_time = models.DateTimeField(auto_now_add=True)


class NotificationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_name = models.CharField(max_length=200)
    notification_text = models.TextField(max_length=400)
    action_type = models.CharField(max_length=50, default="")
    data = JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    date_time = models.DateTimeField(auto_now_add=True)
