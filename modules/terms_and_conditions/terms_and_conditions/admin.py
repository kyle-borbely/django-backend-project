from django.contrib import admin
from django.forms import ClearableFileInput
from django.db import models
from .models import TermAndCondition

admin.site.register(TermAndCondition)


class TermAndConditionAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "is_active", "created_at", "updated_at")
    list_filter = ("author", "is_active", "created_at", "updated_at")
    search_fields = ("body", "author__email")
    formfield_overrides = {
        models.FileField: {"widget": ClearableFileInput},
    }
