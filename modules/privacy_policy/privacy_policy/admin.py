from django.contrib import admin
from .models import PrivacyPolicy
from django.db import models
from ckeditor.widgets import CKEditorWidget

admin.site.register(PrivacyPolicy)


class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "is_active", "created_at", "updated_at")
    list_filter = ("author", "is_active", "created_at", "updated_at")
    search_fields = ("body", "author__email")
    formfield_overrides = {
        models.TextField: {"widget": CKEditorWidget},
    }
