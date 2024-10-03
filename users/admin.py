from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from users.forms import UserChangeForm, UserCreationForm
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import SimpleListFilter
from calm_darkness_38642.utils import send_email
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.db import transaction
from django.contrib.auth.models import Group

User = get_user_model()


class UserTypeListFilter(SimpleListFilter):
    title = _("user role")
    parameter_name = "user_type"

    def lookups(self, request, model_admin):
        user_types = User.objects.values_list("user_type", flat=True).distinct()
        return [(user_type, _(user_type)) for user_type in user_types]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user_type=self.value())
        else:
            return queryset


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    add_form_template = "admin/auth/add_form.html"
    form = UserChangeForm
    add_form = UserCreationForm

    user_fieldsets = (
        (
            None,
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "contact_number",
                    "user_type",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "contact_number",
                    "user_type",
                ),
            },
        ),
    )

    list_filter = [UserTypeListFilter]
    ordering = ["-is_superuser", "user_type"]
    filter_horizontal = []
    list_display = [
        "first_name",
        "last_name",
        "email",
        "contact_number",
        "is_superuser",
        "user_type",
    ]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "contact_number",
        "is_superuser",
        "user_type",
    ]

    def can_change_user(self, request):
        return request.user.has_perm("auth.change_user")

    def get_list_display_links(self, request, list_display):
        if self.can_change_user(request):
            return ("user_type",)
        return None

    view_on_site = False

    def get_queryset(self, request):
        return super().get_queryset(request)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Search Admin Panel Users"
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        user = form.save(commit=False)
        user.username = user.email
        user.is_staff = True
        password = User.objects.make_random_password()
        user.set_password(password)

        with transaction.atomic():
            try:
                user.save()
                # Add the user to the 'Admin' group
                admin_group = Group.objects.get(name="Admin")
                admin_group.user_set.add(user)

                current_site = Site.objects.get_current()
                login_url = f"https://{current_site.domain}/admin/login/"

                subject = "[Sloan Leaders] Admin Account Created"
                username = user.username
                context = {
                    "username": username,
                    "password": password,
                    "login_url": login_url,
                }
                html_content = render_to_string("users_email.html", context)
                response = send_email(user.email, subject, html_content)

                # Check if email failed to send
                if not response:
                    # Raise exception to roll back transaction
                    raise Exception("Email could not be sent")
            except Exception as e:
                # Roll back transaction and show error message
                transaction.set_rollback(True)
                messages.set_level(request, messages.ERROR)
                messages.error(request, f"Error: {str(e)}. Admin not created.")

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return self.user_fieldsets

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save_and_continue"] = False
        return super(UserAdmin, self).changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Add Admin User"
        return super(UserAdmin, self).add_view(
            request, form_url, extra_context=extra_context
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Admin user detail"
        return super(UserAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context
        )
