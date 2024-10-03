from django.db import models
from users.models import User

class CalendlyToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='calendly_token')
    access_token = models.CharField(max_length=1000)
    refresh_token = models.CharField(max_length=1000)
    expires_at = models.DateTimeField(null=True, blank=True)
    redirect_url = models.URLField(max_length=2000, null=True, blank=True)
    

    def __str__(self):
        return f"{self.user}'s Calendly token"
