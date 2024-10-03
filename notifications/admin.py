from django.contrib import admin
from .models import Notification
from django.contrib import messages
from django.http import HttpResponseRedirect
from .forms import NotificationForm
from users.models import User
from django.db.models import Q
from calm_darkness_38642.schedular import send_notification
from django.utils import formats

# Register your models here.


@admin.register(Notification)
class Notification_Register(admin.ModelAdmin):
    change_list_template = "notification_admin/list.html"
    list_display_links = None

    def custom_date_time(self, obj):
        return formats.date_format(obj.date_time, "F j, Y g:i A")

    def custom_activate(self, obj):
        if obj.activate == "every_day_at_8":
            return "Every day at 8 AM EST"
        elif obj.activate == "activate_one_time":
            return "One Time"
        return obj.activate

    custom_activate.short_description = "Activate"

    custom_date_time.short_description = "Date and time"
    list_display = [
        "notification_name",
        "notification_text",
        "receiver",
        "custom_activate",
        "custom_date_time",
    ]

    def error_detection(self, error):
        if ("notification_name" in str(error)) and (
            "This field is required." in str(error)
        ):
            return "Notification name is required"
        if ("notification_text" in str(error)) and (
            "This field is required." in str(error)
        ):
            return "Notification Text is required"
        if ("activate" in str(error)) and ("This field is required." in str(error)):
            return "Notification sending time is required"
        else:
            return "Somethong went wrong"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Notifications"
        if request.method == "POST" and (not ("action" in request.POST)):
            form = NotificationForm(request.POST)
            if form.is_valid():
                data = form.clean()
                form.save()
                if data["activate"] != "every_day_at_8":
                    if data["receiver"] == "All":
                        users = User.objects.filter(
                            Q(user_type="Coach") | Q(user_type="Coachee")
                        )
                    else:
                        users = User.objects.filter(user_type=data["receiver"])
                    send_notification(
                        receivers=users,
                        noti_name=data["notification_name"],
                        noti_text=data["notification_text"],
                        action_type="one_time",
                    )

                messages.success(request, "Notification Sent") if data[
                    "activate"
                ] != "every_day_at_8" else messages.success(
                    request, "Notification Saved"
                )

                return HttpResponseRedirect("/admin/notifications/notification/")
            else:
                messages.error(request, self.error_detection(form.errors))
        else:
            form = NotificationForm()
        extra_context["form"] = form

        return super().changelist_view(request=request, extra_context=extra_context)
