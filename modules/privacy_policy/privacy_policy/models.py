from django.db import models
from django.conf import settings
from ckeditor.fields import RichTextField


class PrivacyPolicy(models.Model):
    class Meta:
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policies"

    body = RichTextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Privacy Policy ({self.pk})"
