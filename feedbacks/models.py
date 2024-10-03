from django.db import models
from users.models import User

class Feedback(models.Model):
    class Meta:
        verbose_name = "List of all feedback"
        verbose_name_plural = 'List of all feedbacks'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feedback_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    response_text = models.TextField(blank=True, null=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='feedback_responses')