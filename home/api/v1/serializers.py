import os
import json
import re
import tempfile
from datetime import date, datetime
from django.utils import timezone
from moviepy.editor import VideoFileClip
from django import forms
from rest_framework import serializers
from django.http import HttpRequest
from django.conf import settings
from rest_framework.validators import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from allauth.account import app_settings as allauth_settings
from allauth.account.forms import ResetPasswordForm
from allauth.utils import email_address_exists, generate_unique_username
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from rest_auth.serializers import PasswordResetSerializer
from calm_darkness_38642.utils import (
    CompressedImageField,
    convert_utc_offset,
    get_utc_offset,
)
from modules.django_calendly.calendly.models import CalendlyToken

from clients.models import Client
from coachees.models import (
    Coachee,
    EngagementInfo,
    Session,
    CoacheesReviews,
    CoachReviews,
    CoacheesFinalReportReview,
    CoachFinalReportReview,
    rate_validation,
)

from coaches.models import Coach, Certificate, CoachAvailability
from feedbacks.models import Feedback

from rest_auth.serializers import (
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
)
from notifications.models import NotificationHistory

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "email", "password")
        extra_kwargs = {
            "password": {"write_only": True, "style": {"input_type": "password"}},
            "email": {
                "required": True,
                "allow_blank": False,
            },
        }

    def _get_request(self):
        request = self.context.get("request")
        if (
            request
            and not isinstance(request, HttpRequest)
            and hasattr(request, "_request")
        ):
            request = request._request
        return request

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    _("A user is already registered with this e-mail address.")
                )
        return email

    def create(self, validated_data):
        user = User(
            email=validated_data.get("email"),
            name=validated_data.get("name"),
            username=generate_unique_username(
                [validated_data.get("name"), validated_data.get("email"), "user"]
            ),
        )
        user.set_password(validated_data.get("password"))
        user.save()
        request = self._get_request()
        setup_user_email(request, user, [])
        return user

    def save(self, request=None):
        """rest_auth passes request so we must override to accept it"""
        return super().save()


class UserSerializer(serializers.ModelSerializer):
    user_type_id = serializers.SerializerMethodField()
    calendly_connection_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "user_type",
            "is_new_user",
            "user_type_id",
            "calendly_connection_status"
        ]

    def get_user_type_id(self, obj):
        user_type = obj.user_type

        if user_type == "Client":
            client = obj.client
            if client:
                return client.id
            else:
                return None
        elif user_type == "Coach":
            coach = obj.coach
            if coach:
                return coach.id
            else:
                return None
        elif user_type == "Coachee":
            coachee = obj.coachee
            if coachee:
                return coachee.id
            else:
                return None
        else:
            return None
    
    def get_calendly_connection_status(self, obj):
        user_type = obj.user_type
        if user_type == "Coach":
            return True if CalendlyToken.objects.filter(user=obj).first() else False
        else:
            return None


class PasswordSerializer(PasswordResetSerializer):
    """Custom serializer for rest_auth to solve reset password error"""

    password_reset_form_class = ResetPasswordForm

    def save(self):
        request = self.context.get("request")
        opts = {
            "use_https": request.is_secure(),
            "token_generator": default_token_generator,
            "from_email": getattr(settings, "DEFAULT_FROM_EMAIL"),
            "email_template_name": "registration/password_reset_email.html",
            "subject_template_name": "registration/password_reset_subject.txt",
            "request": request,
        }

        opts.update(self.get_email_options())

        email = self.initial_data["email"]
        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        custom_reset_url = (
            f"https://calm-darkness-38642.botics.co/new-password/{uidb64}/{token}"
        )

        # Send the email with the custom URL using PasswordResetForm
        context = {
            "email": user.email,
            "domain": request.get_host(),
            "site_name": getattr(settings, "SITE_NAME", "Sloan Leaders"),
            "uid": uidb64,
            "user": user,
            "token": token,
            "protocol": "https" if request.is_secure() else "http",
            "custom_reset_url": custom_reset_url,
        }

        subject = "[Sloan Leaders] Password Reset"
        message_text = render_to_string(opts["email_template_name"], context)
        message_html = render_to_string(
            opts["email_template_name"].replace(".html", "_custom.html"), context
        )

        email = EmailMultiAlternatives(
            subject, message_text, opts["from_email"], [user.email]
        )
        email.attach_alternative(message_html, "text/html")
        email.send()


class MobilePasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, min_length=6, required=True)


class CustomChangePasswordForm(SetPasswordForm):
    current_password = forms.CharField(
        label=_("Current password"),
        widget=forms.PasswordInput(attrs={"autofocus": True}),
        strip=False,
        required=True,
    )

    error_messages = {
        **SetPasswordForm.error_messages,
        "invalid_password": _("Invalid current password."),
    }

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields["current_password"].widget.attrs[
            "autocomplete"
        ] = "current-password"
        self.fields["new_password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["new_password2"].widget.attrs["autocomplete"] = "new-password"

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            raise forms.ValidationError(
                self.error_messages["invalid_password"],
                code="invalid_password",
            )
        return current_password


class CustomPasswordResetConfirmSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(
        style={"input_type": "password"}, label=_("New password"), write_only=True
    )
    new_password2 = serializers.CharField(
        style={"input_type": "password"},
        label=_("New password confirmation"),
        write_only=True,
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # Validate the new passwords match
        if attrs["new_password1"] != attrs["new_password2"]:
            raise serializers.ValidationError(
                _("The two password fields did not match.")
            )

        # Validate the new password using Django's built-in password validators
        validate_password(attrs["new_password1"])

        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        new_password1 = validated_data["new_password1"]
        new_password2 = validated_data["new_password2"]

        # Set the new password for the user
        user.set_password(new_password1)
        user.save()

        return user


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        # add current_password as a required field
        self.fields["current_password"].required = True


class CustomPasswordChangeSerializer(PasswordChangeSerializer):
    current_password = serializers.CharField(
        style={"input_type": "password"}, label=_("Current password"), write_only=True
    )
    new_password1 = serializers.CharField(
        style={"input_type": "password"}, label=_("New password"), write_only=True
    )
    new_password2 = serializers.CharField(
        style={"input_type": "password"},
        label=_("New password confirmation"),
        write_only=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # add current_password as a required field
        self.fields["current_password"].required = True

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("The current password is incorrect."))
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        form = CustomChangePasswordForm(user, self.validated_data)
        if form.is_valid():
            form.save(**kwargs)
            return user

        raise serializers.ValidationError(form.errors)


class ClientSerializer(serializers.ModelSerializer):
    profile_picture = CompressedImageField(write_only=True, required=False)
    profile_picture_url = serializers.SerializerMethodField(
        "get_presigned_profile_picture_url"
    )

    class Meta:
        model = Client
        fields = [
            "id",
            "profile_picture",
            "profile_picture_url",
            "client_name",
            "industry",
            "email",
            "city",
            "state",
            "zip_code",
            "contact_name",
            "contact_number",
            "company_employees",
        ]
        read_only_fields = ("id",)

    def get_presigned_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()

    def update(self, instance, validated_data):
        instance.client_name = validated_data.get("client_name", instance.client_name)
        instance.industry = validated_data.get("industry", instance.industry)
        instance.state = validated_data.get("state", instance.state)
        instance.city = validated_data.get("city", instance.city)
        instance.zip_code = validated_data.get("zip_code", instance.zip_code)
        instance.contact_name = validated_data.get(
            "contact_name", instance.contact_name
        )
        instance.contact_number = validated_data.get(
            "contact_number", instance.contact_number
        )
        instance.company_employees = validated_data.get(
            "company_employees", instance.company_employees
        )
        # Check if profile picture is required
        profile_picture_required = (
            "profile_picture" not in validated_data and not instance.profile_picture
        )
        # Update profile picture if provided, otherwise keep the existing one
        profile_picture = validated_data.get("profile_picture")
        if profile_picture:
            instance.profile_picture.save(
                profile_picture.name, profile_picture, save=False
            )
        elif profile_picture_required:
            raise serializers.ValidationError(
                {"detail": "Please provide a profile picture."}
            )
        instance.save()
        return instance


class CoacheeSerializer(serializers.ModelSerializer):
    profile_picture = CompressedImageField(write_only=True, required=False)
    profile_picture_url = serializers.SerializerMethodField(
        "get_presigned_profile_picture_url"
    )
    client_name = serializers.CharField(source="client.client_name", read_only=True)

    class Meta:
        model = Coachee
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "title",
            "contact_number",
            "department",
            "city",
            "zip_code",
            "profile_picture",
            "profile_picture_url",
            "client_name",
        )

    def _get_request(self):
        request = self.context.get("request")
        if (
            request
            and not isinstance(request, HttpRequest)
            and hasattr(request, "_request")
        ):
            request = request._request
        return request

    def get_presigned_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = (
            "id",
            "name",
        )
        read_only_fields = ("id",)


class CoachSerializer(serializers.ModelSerializer):
    certificates = CertificateSerializer(many=True, required=False)
    profile_picture = CompressedImageField(write_only=True, required=False)
    profile_picture_url = serializers.SerializerMethodField(
        "get_presigned_profile_picture_url"
    )
    intro_video = serializers.FileField(write_only=True, required=False)
    intro_video_url = serializers.SerializerMethodField("get_presigned_intro_video_url")

    class Meta:
        model = Coach
        fields = (
            "id",
            "first_name",
            "last_name",
            "years_of_experience",
            "bio",
            "city",
            "zip_code",
            "profile_picture",
            "profile_picture_url",
            "intro_video",
            "intro_video_url",
            "certificates",
        )
        read_only_fields = ("id",)

    def get_presigned_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()

    def get_presigned_intro_video_url(self, obj):
        return obj.get_intro_video_url()

    def validate_video(self, value):
        if value:
            # Save the uploaded video to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_path = temp_file.name
                for chunk in value.chunks():
                    temp_file.write(chunk)

            try:
                # Get the duration of the video
                clip = VideoFileClip(temp_path)
                duration = clip.duration
                clip.close()

                # Check if duration exceeds 50 seconds
                if duration > 50:
                    raise serializers.ValidationError(
                        {"detail": "Video duration should not exceed 50 seconds."}
                    )
            finally:
                # Delete the temporary file
                os.remove(temp_path)

        return value

    def update(self, instance, validated_data):
        # Validate certificates data
        certificates_data = self.initial_data.get("certificates", [])
        if certificates_data:
            certificates_data = json.loads(certificates_data)
            certificates_serializer = CertificateSerializer(
                data=certificates_data, many=True
            )
            if not certificates_serializer.is_valid():
                raise serializers.ValidationError(certificates_serializer.errors)

            # Get existing certificate names
            existing_certificate_names = set(
                instance.certificates.values_list("name", flat=True)
            )

            # Update certificates field
            for certificate_data in certificates_data:
                certificate_id = certificate_data.get("id")
                certificate_name = certificate_data.get("name")

                if certificate_name in existing_certificate_names:
                    continue  # Skip creating duplicate certificates

                if certificate_id:
                    # If certificate id is provided, update existing certificate
                    certificate = Certificate.objects.get(id=certificate_id)
                    certificate.name = certificate_name
                    certificate.save()
                else:
                    # If certificate id is not provided, create a new certificate
                    certificate = Certificate(name=certificate_name)
                    certificate.save()
                    instance.certificates.add(certificate)

        # Update other fields
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.years_of_experience = validated_data.get(
            "years_of_experience", instance.years_of_experience
        )
        instance.bio = validated_data.get("bio", instance.bio)
        instance.city = validated_data.get("city", instance.city)
        instance.zip_code = validated_data.get("zip_code", instance.zip_code)
        # Check if profile picture is required
        profile_picture_required = (
            "profile_picture" not in validated_data and not instance.profile_picture
        )

        # Update profile picture if provided, otherwise keep the existing one
        profile_picture = validated_data.get("profile_picture")
        if profile_picture:
            instance.profile_picture = profile_picture
        elif profile_picture_required:
            raise serializers.ValidationError(
                {"detail": "Please provide a profile picture."}
            )

        intro_video = validated_data.get("intro_video")
        if intro_video:
            self.validate_video(intro_video)
            instance.intro_video = intro_video
        else:
            instance.intro_video = instance.intro_video

        instance.save()

        return instance


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["feedback_text"]


class CoacheeCoachEngagementSerializer(serializers.ModelSerializer):
    coach = CoachSerializer(read_only=True)
    first_name = serializers.CharField(source="coach.first_name")
    last_name = serializers.CharField(source="coach.last_name")
    years_of_experience = serializers.IntegerField(source="coach.years_of_experience")
    bio = serializers.CharField(source="coach.bio")
    profile_picture_url = serializers.SerializerMethodField(
        "get_presigned_profile_picture_url"
    )
    num_sessions = serializers.SerializerMethodField()

    def get_num_sessions(self, obj):
        return obj.coachee.num_sessions

    def get_presigned_profile_picture_url(self, obj):
        return obj.coach.get_profile_picture_url()

    engagement_info_id = serializers.IntegerField(source="id")

    class Meta:
        model = EngagementInfo
        fields = (
            "engagement_info_id",
            "coachee_id",
            "coach_id",
            "coach",
            "is_chemistry_call",
            "is_assigned",
            "num_sessions",
            "first_name",
            "last_name",
            "years_of_experience",
            "bio",
            "profile_picture_url",
        )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        engagement_info_id = ret.pop("engagement_info_id")
        ret = {"engagement_info_id": engagement_info_id, **ret}
        ret.pop("coach")
        return ret


class UTCTimezoneOffsetField(serializers.Field):
    def to_internal_value(self, data):
        if not re.match(r"^[+-]\d{2}:\d{2}$", data):
            raise serializers.ValidationError(
                "Invalid UTC offset format. Use a valid format like '+05:00' or '-04:00'."
            )
        return data

    def to_representation(self, obj):
        return obj


class CoachAvailabilityListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    start_time = serializers.TimeField(
        format="%I:%M%p",
        input_formats=["%I:%M%p"],
        error_messages={
            "invalid": "Invalid time format. Use the following format: hh:mm[AM|PM].",
        },
    )
    end_time = serializers.TimeField(
        format="%I:%M%p",
        input_formats=["%I:%M%p"],
        error_messages={
            "invalid": "Invalid time format. Use the following format: hh:mm[AM|PM].",
        },
    )
    date = serializers.DateField(
        format="%Y-%m-%d",
        error_messages={
            "invalid": "Invalid date format. Use the following format: YYYY-MM-DD.",
        },
    )
    utc_offset = UTCTimezoneOffsetField(required=False)

    class Meta:
        model = CoachAvailability
        fields = ("id", "date", "start_time", "end_time", "utc_offset")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["timezone"] = settings.TIME_ZONE
        representation["utc_offset"] = get_utc_offset(settings.TIME_ZONE)
        return representation

    def validate(self, data):
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        date = data.get("date")
        utc_offset = data.get("utc_offset")
        start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")

        updated_values = convert_utc_offset(
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            utc_offset=utc_offset,
        )

        data["start_time"] = updated_values[0]
        data["end_time"] = updated_values[1]
        data["date"] = updated_values[2]
        data["utc_offset"] = get_utc_offset(settings.TIME_ZONE)
        return data


class CoachAvailabilitySerializer(serializers.ModelSerializer):
    start_time = serializers.TimeField(
        format="%I:%M%p",
        input_formats=["%I:%M%p"],
        error_messages={
            "invalid": "Invalid time format. Use the following format: hh:mm[AM|PM].",
        },
    )
    end_time = serializers.TimeField(
        format="%I:%M%p",
        input_formats=["%I:%M%p"],
        error_messages={
            "invalid": "Invalid time format. Use the following format: hh:mm[AM|PM].",
        },
    )
    date = serializers.DateField(
        format="%Y-%m-%d",
        error_messages={
            "invalid": "Invalid date format. Use the following format: YYYY-MM-DD.",
        },
    )
    utc_offset = UTCTimezoneOffsetField(required=False)
    is_reserved = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = CoachAvailability
        fields = ("id", "date", "start_time", "end_time", "utc_offset", "is_reserved")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["timezone"] = settings.TIME_ZONE
        representation["utc_offset"] = get_utc_offset(settings.TIME_ZONE)
        return representation

    def validate(self, data):
        coach = self.context.get("coach")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        date = data.get("date")
        utc_offset = data.get("utc_offset")
        start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")

        updated_values = convert_utc_offset(
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            utc_offset=utc_offset,
        )

        data["start_time"] = updated_values[0]
        data["end_time"] = updated_values[1]
        data["date"] = updated_values[2]
        data["utc_offset"] = get_utc_offset(settings.TIME_ZONE)
        start_time_conflicting_slots = (
            CoachAvailability.objects.filter(coach=coach)
            .filter(date=updated_values[2])
            .filter(start_time__lte=updated_values[0])
            .filter(end_time__gt=updated_values[0])
        )
        end_time_conflicting_slots = (
            CoachAvailability.objects.filter(coach=coach)
            .filter(date=updated_values[2])
            .filter(start_time__lte=updated_values[1])
            .filter(end_time__gt=updated_values[1])
        )
        if start_time_conflicting_slots.exists() or end_time_conflicting_slots.exists():
            raise serializers.ValidationError(
                "Slots cannot overlap. Please choose a time that doesn't conflict with existing slots"
            )
        return data


class CoacheeViewSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField(
        "get_presigned_profile_picture_url"
    )

    class Meta:
        model = Coachee
        fields = ("id", "first_name", "last_name", "profile_picture_url")

    def get_presigned_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()


class SessionSerializer(serializers.ModelSerializer):
    CALL_TYPE_CHOICES = [
        ("Chemistry Call", "Chemistry Call"),
        ("Coaching Session", "Coaching Session"),
    ]

    start_time = serializers.TimeField(
        format="%I:%M%p",
        input_formats=["%I:%M%p"],
        error_messages={
            "invalid": "Invalid time format. Use the following format: hh:mm[AM|PM].",
        },
    )
    end_time = serializers.TimeField(
        format="%I:%M%p",
        input_formats=["%I:%M%p"],
        error_messages={
            "invalid": "Invalid time format. Use the following format: hh:mm[AM|PM].",
        },
    )
    call_type = serializers.ChoiceField(
        choices=CALL_TYPE_CHOICES,
        error_messages={
            "invalid_choice": "Invalid call type. Valid call types are: [Chemistry Call] or [Coaching Session].",
        },
    )
    session_date = serializers.DateField(
        input_formats=["%Y-%m-%d", "%Y-%m"],
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "Invalid date format. Use the following format: YYYY-MM-DD or YYYY-MM.",
        },
    )
    utc_offset = UTCTimezoneOffsetField(required=False)
    is_notify = serializers.BooleanField(read_only=True, default=False)
    is_reviewed_by_coach = serializers.BooleanField(read_only=True, default=False)
    is_reviewed_by_coachee = serializers.BooleanField(read_only=True, default=False)

    def validate_session_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Session date cannot be in the past.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["timezone"] = settings.TIME_ZONE
        representation["utc_offset"] = get_utc_offset(settings.TIME_ZONE)
        return representation

    class Meta:
        model = Session
        fields = (
            "id",
            "engagement_info_id",
            "session_date",
            "start_time",
            "end_time",
            "call_type",
            "is_notify",
            "utc_offset",
            "is_reviewed_by_coach",
            "is_reviewed_by_coachee",
        )

    def validate(self, data):
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        date = data.get("session_date")
        utc_offset = data.get("utc_offset")
        start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")

        updated_values = convert_utc_offset(
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            utc_offset=utc_offset,
        )

        data["start_time"] = updated_values[0]
        data["end_time"] = updated_values[1]
        data["session_date"] = updated_values[2]
        data["utc_offset"] = get_utc_offset(settings.TIME_ZONE)
        return data


class EngagementInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EngagementInfo
        fields = ("coachee_id", "id", "is_chemistry_call")


class CoachCalendarSerializer(serializers.Serializer):
    coachee = CoacheeViewSerializer()
    sessions = SessionSerializer(many=True)

    class Meta:
        model = EngagementInfo
        fields = ("coachee", "sessions")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        current_date = date.today()
        filtered_sessions = [
            session
            for session in representation["sessions"]
            if session["session_date"] >= current_date.isoformat()
        ]
        return {
            **representation["coachee"],
            "sessions": filtered_sessions,
        }


class CoachViewSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField(
        "get_presigned_profile_picture_url"
    )

    class Meta:
        model = Coach
        fields = ("id", "first_name", "last_name", "profile_picture_url")

    def get_presigned_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()


class CoacheeEngagementInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EngagementInfo
        fields = ("coach_id", "id", "is_chemistry_call")


class CoacheeCalendarSerializer(serializers.Serializer):
    coach = CoachViewSerializer()
    sessions = SessionSerializer(many=True)

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Filter sessions to include only the current date onwards
        current_date = date.today()
        filtered_sessions = [
            session
            for session in representation["sessions"]
            if session["session_date"] >= current_date.isoformat()
        ]

        return {
            **representation["coach"],
            "sessions": filtered_sessions,
        }


class CoacheeCalendarFilterSerializer(serializers.Serializer):
    coach = CoachViewSerializer()
    sessions = serializers.SerializerMethodField()

    def get_sessions(self, obj):
        # Retrieve session_date, session_month, session_year, and timezone from the context
        session_date = self.context.get("session_date")
        session_month = self.context.get("session_month")
        session_year = self.context.get("session_year")

        # Filter sessions based on the session_date, session_month, and session_year
        filtered_sessions = obj.sessions.all()
        current_date = date.today()
        filtered_sessions = filtered_sessions.filter(session_date__gte=current_date)
        if session_date:
            filtered_sessions = filtered_sessions.filter(session_date=session_date)
        elif session_year and session_month:
            filtered_sessions = filtered_sessions.filter(
                session_date__year=session_year, session_date__month=session_month
            )

        # Serialize the filtered sessions
        session_serializer = SessionSerializer(filtered_sessions, many=True)
        return session_serializer.data

    def to_representation(self, obj):
        representation = super().to_representation(obj)
        return {
            **representation["coach"],
            "sessions": representation["sessions"],
        }


class CoachCalendarFilterSerializer(serializers.Serializer):
    coachee = CoacheeViewSerializer()
    sessions = serializers.SerializerMethodField()

    def get_sessions(self, obj):
        # Retrieve session_date, session_month, session_year, and timezone from the context
        session_date = self.context.get("session_date")
        session_month = self.context.get("session_month")
        session_year = self.context.get("session_year")

        # Filter sessions based on the session_date, session_month, and session_year
        filtered_sessions = obj.sessions.all()
        current_date = date.today()
        filtered_sessions = filtered_sessions.filter(session_date__gte=current_date)
        if session_date:
            filtered_sessions = filtered_sessions.filter(session_date=session_date)
        elif session_year and session_month:
            filtered_sessions = filtered_sessions.filter(
                session_date__year=session_year, session_date__month=session_month
            )
        # Serialize the filtered sessions
        session_serializer = SessionSerializer(filtered_sessions, many=True)
        return session_serializer.data

    def to_representation(self, obj):
        representation = super().to_representation(obj)
        return {
            **representation["coachee"],
            "sessions": representation["sessions"],
        }


class CoachReviewsSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(max_length=300, allow_blank=True)
    rate = serializers.IntegerField(required=True)

    class Meta:
        model = CoachReviews
        fields = ["rate", "comment"]

    def validate(self, data):
        """
        Here we check that the passed session id is valid or not if valid then we check the review is already submitted or not
        """
        rate = data.get("rate")
        if rate <= 0 or rate > 5:
            raise ValidationError("Please fill all the mandatory fields.")
        session_id = self.context["session_id"]
        session_obj = Session.objects.filter(id=session_id)
        if session_obj.exists():
            review_obj = CoachReviews.objects.filter(session_id=session_id)
            if review_obj.exists():
                raise ValidationError("already submitted.")
            return data
        else:
            raise ValidationError("Invalid Session Id.")


class CoacheesReviewsSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(max_length=300, allow_blank=True)
    rate_1 = serializers.IntegerField(required=True)

    class Meta:
        model = CoacheesReviews
        fields = ["rate_1", "comment"]

    def validate(self, data):
        """
        Here we check that the passed session id is valid or not if valid then we check the review is already submitted or not
        """
        rate_1 = data.get("rate_1")
        if rate_1 <= 0 or rate_1 > 5:
            raise ValidationError("Please fill all the mandatory fields.")
        session_id = self.context["session_id"]
        session_obj = Session.objects.filter(id=session_id)
        if session_obj.exists():
            review_obj = CoacheesReviews.objects.filter(session_id=session_id)
            if review_obj.exists():
                raise ValidationError("Review for this session is already submitted")
            return data
        else:
            raise ValidationError("Invalid Session Id.")


class FinalReportReviewSerializer(serializers.Serializer):
    comment = serializers.CharField(
        max_length=300,
        error_messages={
            "required": "Comment is required.",
            "blank": "Comment is required.",
        },
    )
    rate_1 = serializers.IntegerField(required=True)
    rate_2 = serializers.IntegerField(required=True)
    rate_3 = serializers.IntegerField(required=True)
    rate_4 = serializers.IntegerField(required=True)

    def validate(self, data):
        validation = rate_validation(
            rate_1=data.get("rate_1"),
            rate_2=data.get("rate_2"),
            rate_3=data.get("rate_3"),
            rate_4=data.get("rate_4"),
        )
        # validation of rates values
        if validation is not None:
            raise ValidationError(validation)

        engagement_id = self.context["engagement_id"]
        user_type = self.context["user_type"]

        try:
            # confirming the engagement id
            engagement_info_obj = EngagementInfo.objects.get(id=engagement_id)
        except:
            raise ValidationError("Invalid Engagement Id.")

        # getting all sessions
        session_objects = Session.objects.filter(
            engagement_info_id=engagement_id, call_type="Coaching Session"
        )

        # on the bases of user_type we check that the review is submitted or not
        if user_type == "coach":
            coach_review_obj = CoachFinalReportReview.objects.filter(
                engagement_info_id=engagement_id
            )
            if coach_review_obj.exists():
                raise ValidationError("Review already submitted.")

            # checking the reviews of all sessions is submitted or not for coach

            if session_objects.exists():
                if session_objects.count() == engagement_info_obj.coachee.num_sessions:
                    for obj in session_objects:
                        try:
                            CoachReviews.objects.get(session_id=obj.id)
                        except:
                            raise ValidationError(
                                "Session review is missing, Please review the all completed sessions."
                            )
                    return data
                else:
                    raise ValidationError(
                        "Final report cannot be submitted until all session reviews have been completed."
                    )
            else:
                raise ValidationError("Sessions not found.")

        elif user_type == "coachee":
            coachee_review_obj = CoacheesFinalReportReview.objects.filter(
                engagement_info_id=engagement_id
            )
            if coachee_review_obj.exists():
                raise ValidationError("Review already submitted.")

            # checking the reviews of all sessions is submitted or not for coachee
            if session_objects.exists():
                if session_objects.count() == engagement_info_obj.coachee.num_sessions:
                    for obj in session_objects:
                        try:
                            CoacheesReviews.objects.get(session_id=obj.id)
                        except:
                            raise ValidationError(
                                "Session review is missing, Please review the all completed sessions."
                            )
                    return data
                else:
                    raise ValidationError(
                        "Final report cannot be submitted until all session reviews have been completed."
                    )
            else:
                raise ValidationError("Sessions not found.")


class NotificationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationHistory
        fields = [
            "id",
            "notification_name",
            "notification_text",
            "action_type",
            "data",
            "is_read",
            "date_time",
        ]


class ClientCoacheeEngagementDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = EngagementInfo
        fields = [
            "id",
            "coachee",
            "coach",
            "is_chemistry_call",
            "is_assigned",
            "num_scheduled_sessions",
            "start_date",
            "end_date",
        ]


class SessionCallTokenSerializer(serializers.Serializer):
    room_sid = serializers.CharField(
        max_length=300,
        error_messages={
            "required": "Room sid is required.",
            "blank": "Room sid is required.",
        },
    )
    user_id = serializers.IntegerField(error_messages={
            "required": "User id is required.",
            "blank": "User id is required.",
        },)
