from django.contrib import admin
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Coach
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.utils.html import format_html
from calm_darkness_38642.utils import send_email
from django.urls import reverse as admin_reverse
from django.urls import path
from django.http import HttpResponseRedirect
from django.db import IntegrityError

from home.storage_backends import generate_presigned_url

User = get_user_model()


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    change_form_template = "admin/coaches/change_form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def user_type(self, obj):
        return obj.user.user_type

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("certificates")
        return qs

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            presigned_url = generate_presigned_url(obj.profile_picture.name)
            return format_html(
                '<img src="{}" width="100" height="100" />', presigned_url
            )
        else:
            return "No image available"

    get_profile_picture.short_description = "Profile Picture"

    def get_intro_video(self, obj):
        if obj.intro_video:
            video_url = generate_presigned_url(obj.intro_video.name)
            return format_html(
                f'<div class="intro-video-container">'
                f'<video width="320" height="240" controls><source src="{video_url}" type="video/mp4"></video>'
                f'<a href="{admin_reverse("admin:coaches_coach_delete_video", args=[obj.id])}" style="display: inline-block; margin-left: 10px; padding: 5px 10px; background-color: #a41515; color: white; text-decoration: none; border-radius: 5px;">Delete Video</a>'
                f"</div>"
            )
        else:
            return "No video available"

    get_intro_video.short_description = "Video presentation"

    def delete_intro_video(self, request, id):
        coach = Coach.objects.get(id=id)
        coach.delete_intro_video()
        return HttpResponseRedirect(
            admin_reverse("admin:coaches_coach_change", args=[id])
        )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:id>/delete-video/",
                self.admin_site.admin_view(self.delete_intro_video),
                name="coaches_coach_delete_video",
            )
        ]
        return my_urls + urls

    def certificates_list(self, obj):
        return ", ".join(c.name for c in obj.certificates.all())

    certificates_list.short_description = "Certificates and documentation"

    def years_of_coaching_experience(self, obj):
        if not obj.years_of_experience:
            return ""
        return obj.years_of_experience

    years_of_coaching_experience.short_description = "Years of coaching experience"

    # specify the fields to be displayed in the add form
    add_fields = ("first_name", "last_name", "email")
    change_fields = (
        "get_profile_picture",
        "first_name",
        "last_name",
        "email",
        "years_of_experience",
        "bio",
        "city",
        "zip_code",
        "get_intro_video",
        "certificates_list",
    )
    list_display = [
        "first_name",
        "last_name",
        "email",
        "years_of_coaching_experience",
        "city",
        "user_type",
    ]
    readonly_fields = ()
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "years_of_experience",
        "city",
    ]
    list_display_links = None

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:
            # add the fields you want to make read-only
            readonly_fields += [
                "get_profile_picture",
                "email",
                "get_intro_video",
                "certificates_list",
            ]
        return readonly_fields

    @transaction.atomic()
    def save_model(self, request, obj, form, change):
        try:
            if not change:
                normalize_email = obj.email.lower()
                # Check if email already exists in User model
                if User.objects.filter(email=normalize_email).exists():
                    raise IntegrityError(f"Email '{normalize_email}' already exists.")

                # Create a new User with user_type='Coach'
                password = User.objects.make_random_password()
                user = User.objects.create_user(
                    username=normalize_email,
                    email=normalize_email,
                    password=password,
                    user_type="Coach",
                    is_new_user=True,
                    first_name=obj.first_name,
                    last_name=obj.last_name,
                )

                current_site = Site.objects.get_current()
                login_url = f"https://{current_site.domain}"

                subject = "[Sloan Leaders] Coach Account Created"
                username = user.username
                context = {
                    "username": username,
                    "password": password,
                    "login_url": login_url,
                }
                html_content = render_to_string("coaches_email.html", context)
                response = send_email(user.email, subject, html_content)

                if not response:
                    # rollback the transaction and show error message
                    transaction.set_rollback(True)
                    # show error message
                    messages.set_level(request, messages.ERROR)
                    messages.error(
                        request, "Error: Email could not be sent. Coach not created."
                    )
                else:
                    # Assign the user_type of the Coach and save the object
                    obj.user = user
                    obj.email = normalize_email
                    obj.save()
            else:
                # If it's an update, just save the object
                obj.save()
        except IntegrityError as e:
            messages.set_level(request, messages.ERROR)
            messages.error(request, str(e))
            return

    # override the add_view method
    def add_view(self, request, form_url="", extra_context=None):
        # display only the fields specified in add_fields
        self.fields = self.add_fields
        extra_context = extra_context or {}
        app_label, model_name = self.model._meta.app_label, self.model._meta.model_name
        extra_context["title"] = "Add {model_name}".format(
            model_name=model_name.capitalize()
        )
        extra_context["show_save"] = True
        extra_context["save_label"] = "Save"
        extra_context["show_save_and_add_another"] = True
        return super().add_view(request, form_url, extra_context)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        try:
            search_term_as_int = int(search_term)
            queryset |= self.model.objects.filter(id=search_term_as_int)
        except ValueError:
            pass
        return queryset, use_distinct

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Search Coaches"
        extra_context["add_button_label"] = "Add Coach"
        return super().changelist_view(request, extra_context=extra_context)

    list_display_links = ("email",)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self.fields = self.change_fields
        extra_context = extra_context or {}
        extra_context["title"] = "Coach detail"
        # Customize the submit buttons
        extra_context["show_save"] = True
        extra_context["show_save_as_new"] = False
        extra_context["show_save_and_add_another"] = False
        extra_context["show_delete_link"] = True

        # Override the submit button labels
        extra_context["save_label"] = "Save"
        return super().change_view(request, object_id, form_url, extra_context)
