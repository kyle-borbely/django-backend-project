from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from coachees.models import Coachee, EngagementInfo, Session
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


@admin.register(Coachee)
class CoacheeAdmin(admin.ModelAdmin):
    change_form_template = "admin/coachees/coachee_detail.html"

    def assign_coach_button(self, obj):
        if obj.coaching_status == "Assigned":
            url = reverse("coachees:assign_coach", args=[obj.pk])
            return format_html(
                '<a href="{}" style="background-color: #F0F0F0;border: 1px solid #ccc; color: black;" class="button">Assign Coach</a>',
                url,
            )
        elif obj.coaching_status == "Not Assigned":
            url = reverse("coachees:assign_coach", args=[obj.pk])
            return format_html(
                '<a href="{}" style="background-color: #417690;color: white;" class="button">Assign Coach</a>',
                url,
            )
        else:
            return ""

    assign_coach_button.short_description = "Action"
    assign_coach_button.allow_tags = True

    def engagement_status_color(self, obj):
        if obj.engagement_status in ["Start Engagement", "End Engagement"]:
            return format_html(
                '<span style="color: green;">{}</span>', obj.engagement_status
            )
        else:
            return obj.engagement_status

    engagement_status_color.short_description = "Engagement Status"

    list_display = (
        "first_name",
        "last_name",
        "email",
        "client",
        "engagement_status_color",
        "coaching_status",
        "assign_coach_button",
    )
    list_filter = ("client__client_name", "coaching_status", "engagement_status")
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "client__client_name",
        "engagement_status",
        "coaching_status",
    )
    list_display_links = ("email",)
    readonly_fields = ()
    change_fields = (
        "first_name",
        "last_name",
        "email",
        "title",
        "department",
        "city",
        "zip_code",
        "contact_number",
        "client",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:
            # add the fields you want to make read-only
            readonly_fields += [
                "get_profile_picture",
                "email",
                "client",
            ]
        return readonly_fields

    def has_add_permission(self, request):
        # Disable the 'Add' button for Coachee
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Search Coachees"
        return super().changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self.fields = self.change_fields
        # Retrieve the related sessions
        coachee = self.get_object(request, object_id)
        current_date = timezone.now().date()
        current_time = timezone.now().time()
        # Retrieve past sessions
        past_sessions = Session.objects.filter(
            engagement_info__coachee=coachee,
            end_time__lt=current_time,
            call_type="Coaching Session",
        )
        # Retrieve scheduled sessions
        scheduled_sessions = Session.objects.filter(
            engagement_info__coachee=coachee,
            session_date__gte=current_date,
            call_type="Coaching Session",
        )
        # Retrieve the coach information from the related engagement info
        coaches = []
        for session in scheduled_sessions:
            coaches.append(session.engagement_info.coach)
        # past engagements
        past_engagements = EngagementInfo.objects.filter(
            coachee_id=object_id, end_date__isnull=False, is_assigned=True
        )
        engagements = EngagementInfo.objects.filter(coachee=coachee, is_assigned=True)
        extra_context = extra_context or {}
        extra_context["title"] = "Coachee detail"
        extra_context["engagements"] = engagements
        extra_context["past_sessions"] = past_sessions
        extra_context["scheduled_sessions"] = scheduled_sessions
        extra_context["coaches"] = coaches
        extra_context["past_engagements"] = past_engagements

        return super().change_view(request, object_id, form_url, extra_context)
