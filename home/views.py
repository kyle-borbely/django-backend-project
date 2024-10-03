from django.shortcuts import render
from rest_auth.views import (
    PasswordResetView,
    PasswordResetConfirmView,
    PasswordChangeView,
)

from home.api.v1.serializers import (
    PasswordSerializer,
    CustomPasswordResetConfirmSerializer,
    CustomPasswordChangeSerializer,
    MobilePasswordResetSerializer,
    VerifyOTPSerializer,
)
from rest_framework.generics import GenericAPIView
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from django.conf import settings
from django.template.loader import render_to_string
from .models import EmailOTP
from django.core.mail import EmailMultiAlternatives

User = get_user_model()


def home(request):
    packages = [
        {
            "name": "django-allauth",
            "url": "https://pypi.org/project/django-allauth/0.38.0/",
        },
        {
            "name": "django-bootstrap4",
            "url": "https://pypi.org/project/django-bootstrap4/0.0.7/",
        },
        {
            "name": "djangorestframework",
            "url": "https://pypi.org/project/djangorestframework/3.9.0/",
        },
    ]
    context = {"packages": packages}
    return render(request, "home/index.html", context)


class PasswordResetView(PasswordResetView):
    def get_serializer_class(self):
        return PasswordSerializer


class MobilePasswordResetView(GenericAPIView):
    serializer_class = MobilePasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate the email address
        email = serializer.validated_data["email"]

        # Check if the user with this email address exists
        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return Response(
                {"detail": "No user found with this email address."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if an OTP instance exists for this user and email
        otp_instance, created = EmailOTP.objects.get_or_create(user=user, email=email)

        # Generate an OTP and send it to the user's email address
        if not created:
            otp_instance.generate_otp_secret()

        otp = otp_instance.send_otp()

        subject = "[Sloan Leaders] Password Reset"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]
        context = {"otp": otp}
        html_content = render_to_string(
            "registration/password_reset_otp_email.html", context
        )
        text_content = f"Your OTP is {otp}"
        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return Response(
            {"detail": _("OTP sent to your email address.")}, status=status.HTTP_200_OK
        )


class VerifyOTPView(APIView):
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the validated user and otp from the serializer
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        # Check if the user with this email address exists
        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return Response(
                {"detail": "No user found with this email address."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            otp_instance = EmailOTP.objects.get(
                user=user,
                email=email,
                verified=False,
            )
        except EmailOTP.DoesNotExist:
            return Response(
                {"detail": "Invalid OTP."}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify the OTP
        if not otp_instance.verify_otp(otp):
            return Response(
                {"detail": "Invalid OTP."}, status=status.HTTP_404_NOT_FOUND
            )

        otp_instance.verified = True
        otp_instance.save()

        # Generate the uidb64 and token for password reset
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        return Response(
            {
                "uidb64": uidb64,
                "token": token,
            },
            status=status.HTTP_200_OK,
        )


class CustomPasswordResetConfirmView(GenericAPIView):
    serializer_class = CustomPasswordResetConfirmSerializer

    def post(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_bytes(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError(_("Invalid user_id value"))

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = urlsafe_base64_encode(uid)

        serializer.validated_data["user_id"] = user_id
        serializer.validated_data["token"] = token
        serializer.validated_data["user"] = user

        serializer.save()

        return Response({"detail": _("Password has been reset with the new password.")})


class CustomPasswordChangeView(PasswordChangeView):
    """
    Override PasswordChangeView to add current password field to serializer.
    """

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        kwargs["data"] = self.request.data  # pass request data as serializer data
        kwargs["data"]["current_password"] = self.request.data.get("current_password")
        return CustomPasswordChangeSerializer(*args, **kwargs)
