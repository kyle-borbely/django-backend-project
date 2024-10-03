from django import forms
from .models import Notification


class NotificationForm(forms.ModelForm):
    receiver_user = (("All", "All"), ("Coachee", "Coachee"), ("Coach", "Coach"))
    receiver = forms.ChoiceField(
        choices=receiver_user,
        widget=forms.Select(
            attrs={
                "class": "vTextField",
                "style": "margin-left: 17px; margin-right: 17px; width: 285px;",
                "id": "id_receiver",
                "maxlength": 110,
            }
        ),
    )
    CHOICE = (
        ("activate_one_time", "One Time"),
        ("every_day_at_8", "Every day at 8 AM EST"),
    )
    activate = forms.ChoiceField(choices=CHOICE)

    class Meta:
        model = Notification
        fields = [
            "notification_name",
            "notification_text",
            "activate",
            "receiver",
        ]
        widgets = {
            "notification_name": forms.TextInput(
                attrs={
                    "class": "vTextField",
                    "style": "margin-left: 17px; margin-right: 17px; width: 275px;",
                    "maxlength": 100,
                    "id": "id_notification_name",
                }
            ),
            "notification_text": forms.TextInput(
                attrs={
                    "class": "vTextField",
                    "style": "margin-left: 17px; margin-right: 17px; width: 275px;",
                    "maxlength": 100,
                    "id": "id_notification_text",
                }
            ),
        }
