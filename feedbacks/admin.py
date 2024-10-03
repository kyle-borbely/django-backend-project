from django.contrib import admin, messages

from django.utils.html import format_html
from clients.models import Client
from coaches.models import Coach
from coachees.models import Coachee
from .models import Feedback
from django.urls import reverse as admin_reverse
from django.core.mail import send_mail
from django.conf import settings

admin.site.empty_value_display = ""


class FeedbackAdmin(admin.ModelAdmin):
    readonly_fields = (
        "display_feedback_text",
        "timestamp",
        "get_profile_picture",
        "get_first_name",
        "get_last_name",
        "get_email",
    )
    fields = (
        "get_profile_picture",
        "get_first_name",
        "get_last_name",
        "get_email",
        "display_feedback_text",
        "response_text",
    )
    list_display = (
        "get_first_name",
        "get_last_name",
        "display_feedback_text",
        "enter_response_button",
    )
    change_form_template = "admin/feedbacks/change_form_custom.html"

    def save_model(self, request, obj, form, change):
        obj.responded_by = request.user

        super().save_model(request, obj, form, change)

    # Response success message
    def response_change(self, request, obj):
        opts = obj._meta
        pk_value = obj._get_pk_val()
        preserved_filters = self.get_preserved_filters(request)
        msg_dict = {
            "name": opts.verbose_name,
            "obj": format_html(
                '<a href="{}">{}</a>',
                admin_reverse(
                    "admin:%s_%s_change" % (opts.app_label, opts.model_name),
                    args=[pk_value],
                ),
                obj,
            ),
        }
        if "_save" in request.POST:
            response_text = request.POST.get("response_text", "")
            send_mail(
                subject="[Sloan Leaders] Feedback Response",
                message=response_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[obj.user.email],
                fail_silently=False,
            )
            msg = format_html("Response sent successfully to the email.", **msg_dict)

            self.message_user(request, msg)

        return self.response_post_save_change(request, obj)

    def get_profile_picture(self, obj):
        user = obj.user
        user_type = user.user_type

        if user_type == "Client":
            try:
                client = Client.objects.get(user=user)
                return format_html(
                    '<img src="{}" width="50" height="50" />',
                    client.profile_picture.url,
                )
            except Client.DoesNotExist:
                pass
        elif user_type == "Coach":
            try:
                coach = Coach.objects.get(user=user)
                return format_html(
                    '<img src="{}" width="50" height="50" />', coach.profile_picture.url
                )
            except Coach.DoesNotExist:
                pass
        elif user_type == "Coachee":
            try:
                coachee = Coachee.objects.get(user=user)
                return format_html(
                    '<img src="{}" width="50" height="50" />',
                    coachee.profile_picture.url,
                )
            except Coachee.DoesNotExist:
                pass

        return ""

    get_profile_picture.short_description = "Profile Picture"

    def get_first_name(self, obj):
        return obj.user.first_name

    get_first_name.short_description = "First Name"

    def get_last_name(self, obj):
        return obj.user.last_name

    get_last_name.short_description = "Last Name"

    def get_email(self, obj):
        return obj.user.email

    get_email.short_description = "Email"

    def enter_response_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Enter Response</a>',
            admin_reverse("admin:feedbacks_feedback_change", args=[obj.pk]),
        )

    enter_response_button.short_description = "Actions"
    enter_response_button.allow_tags = True

    def display_feedback_text(self, obj):
        return obj.feedback_text

    display_feedback_text.short_description = "Feedback"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        feedback = self.get_object(request, object_id)

        # Customize the submit buttons
        extra_context["show_save"] = True
        extra_context["show_save_as_new"] = False
        extra_context["show_save_and_add_another"] = False
        extra_context["show_delete_link"] = True

        # Override the submit button labels
        extra_context["save_label"] = "Send"

        extra_context["title"] = "Feedback Response"
        return super().change_view(request, object_id, form_url, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        extra_context.update(
            {
                "title": f"Feedback response",
            }
        )

        response = super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )

        return response

    def get_object_tools(self, request, opts, obj=None):
        tools = super().get_object_tools(request, opts, obj)
        # Remove the "History" button
        tools = [t for t in tools if t.__name__ != "history_button"]
        return tools

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Users Feedback"
        return super().changelist_view(request, extra_context=extra_context)

    def get_list_display_links(self, request, list_display):
        return None

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "response_text":
            kwargs["label"] = "Response"
        return super().formfield_for_dbfield(db_field, request, **kwargs)


admin.site.register(Feedback, FeedbackAdmin)
