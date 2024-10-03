import pytz
from datetime import datetime, date, timedelta
import json, requests
import calendar
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.authtoken.models import Token
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from calm_darkness_38642.utils import convert_utc_offset, get_utc_offset, make_calendly_get_request, calendly_get_header
from calm_darkness_38642.schedular import notifications
from django.contrib.sites.models import Site
from django.db.models import Avg, Sum
from modules.django_calendly.calendly.models import CalendlyToken

# from icalendar import Calendar, Event, vCalAddress
from rest_framework import permissions, status, serializers, viewsets

from home.api.v1.serializers import (
    SignupSerializer,
    UserSerializer,
    ClientSerializer,
    CoacheeSerializer,
    CoachSerializer,
    FeedbackSerializer,
    CustomPasswordResetConfirmSerializer,
    CoacheeCoachEngagementSerializer,
    CoachAvailabilitySerializer,
    SessionSerializer,
    CoacheeCalendarSerializer,
    CoacheeCalendarFilterSerializer,
    CoachCalendarSerializer,
    CoachCalendarFilterSerializer,
    CoachAvailabilityListSerializer,
    CoachReviewsSerializer,
    CoacheesReviewsSerializer,
    FinalReportReviewSerializer,
    NotificationHistory,
    NotificationHistorySerializer,
    ClientCoacheeEngagementDetailSerializer,
    SessionCallTokenSerializer,
)
from home.api.v1.permissions import (
    IsCoacheeUser,
    IsClientUser,
    IsCoachUser,
    IsClientOrCoacheeUser,
    IsCoachOrCoacheeUser,
    IsCoachCoacheeOrClientUser,
)
from clients.models import Client
from coachees.models import (
    Coachee,
    Session,
    EngagementInfo,
    CoachReviews,
    CoacheesReviews,
    CoachFinalReportReview,
    CoacheesFinalReportReview,
    SessionCall,
)
from coaches.models import Coach, Certificate, CoachAvailability
from feedbacks.models import Feedback

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from calm_darkness_38642.utils import send_email, send_invitation
from django.template.loader import render_to_string

from users.models import User
from fcm_django.models import FCMDevice
from django.db.models import Q
import subprocess
import shlex

from twilio.rest import Client as TwilioClient
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant

# Twilio imports
import twilio.jwt.access_token
import twilio.jwt.access_token.grants
import twilio.rest
from django.http import JsonResponse
import uuid

User = get_user_model()


class SignupViewSet(ModelViewSet):
    serializer_class = SignupSerializer
    http_method_names = ["post"]


class LoginViewSet(ViewSet):
    """Based on rest_framework.authtoken.views.ObtainAuthToken"""

    serializer_class = AuthTokenSerializer

    def create(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        user_serializer = UserSerializer(user)
        return Response({"token": token.key, "user": user_serializer.data})


class CustomPasswordResetConfirmViewSet(ViewSet):
    serializer_class = CustomPasswordResetConfirmSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"detail": "Password has been reset with the new password."}
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientViewSet(ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsClientUser]
    allowed_actions = ("list", "retrieve", "update")

    def get_queryset(self):
        return Client.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        all_data = serializer.data

        for data in all_data:
            if data.get("profile_picture_url") == None:
                data["profile_picture_url"] = ""

            if data.get("state") == None:
                data["state"] = ""

            if data.get("contact_name") == None:
                data["contact_name"] = ""

            if data.get("city") == None:
                data["city"] = ""

            if data.get("zip_code") == None:
                data["zip_code"] = ""

            if data.get("contact_number") == None:
                data["contact_number"] = ""

            if data.get("company_employees") == None:
                data["company_employees"] = 0

        return Response(all_data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        data = serializer.data
        if data.get("profile_picture_url") == None:
            data["profile_picture_url"] = ""

        if data.get("state") == None:
            data["state"] = ""

        if data.get("contact_name") == None:
            data["contact_name"] = ""

        if data.get("city") == None:
            data["city"] = ""

        if data.get("zip_code") == None:
            data["zip_code"] = ""

        if data.get("contact_number") == None:
            data["contact_number"] = ""

        if data.get("company_employees") == None:
            data["company_employees"] = 0

        return Response(data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def delete(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "DELETE" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class CoacheeViewSet(ModelViewSet, CreateModelMixin):
    serializer_class = CoacheeSerializer
    queryset = Coachee.objects.all()
    permission_classes = [IsCoachCoacheeOrClientUser]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Coachee.objects.none()

        if user.user_type == "Client":
            return Coachee.objects.filter(client=user.client)
        elif user.user_type == "Coachee":
            return Coachee.objects.filter(user=user)
        else:
            return Coachee.objects.none()

    def __NoneToEmptyString(self, data):
        if data.get("department") == None:
            data["department"] = ""

        if data.get("profile_picture_url") == None:
            data["profile_picture_url"] = ""

        if data.get("zip_code") == None:
            data["zip_code"] = ""

        if data.get("contact_number") == None:
            data["contact_number"] = ""

        if data.get("city") == None:
            data["city"] = ""

        if data.get("profile_picture_url") == None:
            data["profile_picture_url"] = ""

        if data.get("title") == None:
            data["title"] = ""

        return data

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        all_data = serializer.data

        for data in all_data:
            data = self.__NoneToEmptyString(data)

        return Response(all_data)

    def retrieve(self, request, *args, **kwargs):
        query_obj = self.get_queryset().first()
        if (query_obj == None) and (request.user.user_type == "Coach"):
            obj_id = kwargs.get("pk")
            obj = Coachee.objects.filter(id=obj_id)
            if obj.exists():
                serializer = self.serializer_class(obj.first())
                data = self.__NoneToEmptyString(serializer.data)
                return Response(data)
            else:
                return Response({"detail": "Not found"})
        elif query_obj is not None:
            serializer = self.serializer_class(query_obj)
            data = self.__NoneToEmptyString(serializer.data)
            return Response(data)
        else:
            return Response({"detail": "Not found"})

    @transaction.atomic
    def perform_create(self, serializer):
        request = self.request
        client_user = request.user

        # Check if the user is authenticated and has 'Client' user_type
        if not client_user.is_authenticated or client_user.user_type != "Client":
            return Response(
                {"detail": "You are not authorized to create a Coachee."},
                status=status.HTTP_403_FORBIDDEN,
            )

        email = serializer.validated_data.get("email")
        if User.objects.filter(email=email.lower()).exists():
            raise serializers.ValidationError({"detail": "Email already exists."})

        # Create a new User with user_type='Client'
        password = User.objects.make_random_password()
        user = User.objects.create_user(
            username=serializer.validated_data["email"],
            email=serializer.validated_data["email"],
            password=password,
            user_type="Coachee",
            is_new_user=True,
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
        )

        client_name = client_user.client.client_name
        apple_store_link = settings.APPLE_STORE_LINK
        google_play_link = settings.GOOGLE_PLAY_STORE_LINK
        current_site = Site.objects.get_current()
        login_url = f"https://{current_site.domain}"
        subject = "[Sloan Leaders] Coachee Account Credentials"
        username = user.username
        context = {
            "username": username,
            "password": password,
            "client_name": client_name,
            "login_url": login_url,
        }
        html_content = render_to_string("coachees_email.html", context)
        response = send_email(user.email, subject, html_content)

        if not response:
            # If email sending fails, delete the user object
            transaction.set_rollback(True)
            raise serializers.ValidationError(
                {"detail": "Email could not be sent. Coachee not created."}
            )

        serializer.validated_data["client"] = client_user.client
        # Assign the user object to the Coachee's user field and save it
        serializer.validated_data["user"] = user
        return super().perform_create(serializer)

    @action(detail=False, methods=["get"], url_path="coaches")
    def get_coaches(self, request):
        try:
            # Check if the user is authenticated and has 'Client' user_type
            if not request.user.is_authenticated or request.user.user_type != "Coachee":
                return Response(
                    {"detail": "You are not authorized to get a Coachee's Coaches."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            coachee = request.user.coachee
            if coachee.engagement_infos.filter(
                    is_chemistry_call=True, is_assigned=True
            ).exists():
                engagement_info = coachee.engagement_infos.filter(
                    is_chemistry_call=True, is_assigned=True
                )
            else:
                engagement_info = coachee.engagement_infos.all()
            engagement_info_serializer = CoacheeCoachEngagementSerializer(
                engagement_info, many=True
            )

            return Response(engagement_info_serializer.data, status=status.HTTP_200_OK)
        except Coachee.DoesNotExist:
            return Response(
                {"error": "Coachee not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(methods=["get"], detail=False, url_path="calendar")
    def coachee_calendar(self, request):
        # Assuming the logged-in user is the coachee
        coachee = request.user.coachee

        engagement_infos = (
            EngagementInfo.objects.filter(coachee_id=coachee.id, is_chemistry_call=True)
            .select_related("coach")
            .distinct()
        )

        serializer = CoacheeCalendarSerializer(engagement_infos, many=True)
        for i in serializer.data:
            status = False
            coach_id = i['id']
            coach = Coach.objects.filter(id=coach_id).first()
            i['calendly_connection_status'] = True if CalendlyToken.objects.filter(user=coach.user).first() else False
        return Response(serializer.data)

    @action(
        methods=["get"],
        detail=False,
        url_path=r"calendar/(?P<session_date>\d{4}(?:-\d{2}(?:-\d{2})?)?)?",
    )
    def coachee_calendar_session_date(self, request, session_date=None):
        coachee = request.user.coachee

        if len(session_date) == 10:
            engagement_infos = (
                EngagementInfo.objects.filter(
                    coachee_id=coachee.id,
                    is_chemistry_call=True,
                    sessions__session_date=session_date,
                    sessions__session_date__gte=datetime.now().date(),
                )
                .select_related("coach")
                .distinct()
            )
            serializer = CoacheeCalendarFilterSerializer(
                engagement_infos, context={"session_date": session_date}, many=True
            )
            return Response(serializer.data)

        elif len(session_date) == 7:
            session_year, session_month = session_date.split("-")
            engagement_infos = (
                EngagementInfo.objects.filter(
                    coachee_id=coachee.id,
                    is_chemistry_call=True,
                    sessions__session_date__year=session_year,
                    sessions__session_date__month=session_month,
                    sessions__session_date__gte=datetime.now().date(),
                )
                .select_related("coach")
                .distinct()
            )

            serializer = CoacheeCalendarFilterSerializer(
                engagement_infos,
                context={"session_year": session_year, "session_month": session_month},
                many=True,
            )
            return Response(serializer.data)
        elif len(session_date) == 4:
            session_year = session_date
            engagement_infos = (
                EngagementInfo.objects.filter(
                    coachee_id=coachee.id,
                    is_chemistry_call=True,
                    sessions__session_date__year=session_year,
                    sessions__session_date__gte=datetime.now().date(),
                )
                .select_related("coach")
                .distinct()
            )

            serializer = CoacheeCalendarFilterSerializer(
                engagement_infos, context={"session_year": session_year}, many=True
            )
            return Response(serializer.data)

    def coachee_sessions(self, request, coach_id):
        current_date = datetime.now().date()
        coachee = request.user.coachee
        if coach_id is None:
            return Response(
                {"detail": "coach_id parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessions = Session.objects.filter(
            engagement_info__coachee=coachee,
            engagement_info__coach_id=coach_id,
            engagement_info__is_assigned=True,
            call_type="Coaching Session",
            session_date__gte=current_date,
        )
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if "email" in serializer.validated_data:
            # Remove email from the validated data, email should not be updated.
            serializer.validated_data.pop("email")
        self.perform_update(serializer)
        return Response(serializer.data)


class CoachViewSet(ModelViewSet):
    queryset = Coach.objects.all()
    serializer_class = CoachSerializer
    permission_classes = [IsCoachUser]

    def get_permissions(self):
        if self.action == "list":
            permission_classes = [IsCoachOrCoacheeUser]
        elif self.action == "retrieve":
            permission_classes = [IsCoachCoacheeOrClientUser]
        else:
            permission_classes = self.permission_classes

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "Coach":
            queryset = Coach.objects.filter(user=self.request.user)
        else:
            queryset = super().get_queryset()

        # Apply permission classes to the queryset
        queryset = self.filter_queryset(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        all_data = serializer.data

        for data in all_data:
            if data.get("profile_picture_url") == None:
                data["profile_picture_url"] = ""

            if data.get("bio") == None:
                data["bio"] = ""

            if data.get("years_of_experience") == None:
                data["years_of_experience"] = 0

            if data.get("city") == None:
                data["city"] = ""

            if data.get("zip_code") == None:
                data["zip_code"] = ""

            if data.get("intro_video_url") == None:
                data["intro_video_url"] = ""

        return Response(all_data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        data = serializer.data
        if data.get("profile_picture_url") == None:
            data["profile_picture_url"] = ""

        if data.get("bio") == None:
            data["bio"] = ""

        if data.get("years_of_experience") == None:
            data["years_of_experience"] = 0

        if data.get("city") == None:
            data["city"] = ""

        if data.get("zip_code") == None:
            data["zip_code"] = ""

        if data.get("intro_video_url") == None:
            data["intro_video_url"] = ""

        return Response(data, status=status.HTTP_200_OK)

    # Already created Coach by admin, don't need to expose post method
    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(
        detail=True, methods=["delete"], url_path="certificates/(?P<certificate_id>\d+)"
    )
    def delete_certificate(self, request, pk=None, certificate_id=None):
        # Get the coach and certificate
        coach = self.get_object()
        try:
            certificate = Certificate.objects.get(id=certificate_id)
        except Certificate.DoesNotExist:
            return Response(
                {"detail": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Remove the certificate from the coach's certificates
        coach.certificates.remove(certificate)
        # Delete the certificate object from both tables
        certificate.delete()
        return Response(
            {"detail": "Certificate deleted successfully"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["delete"])
    def delete_intro_video(self, request, pk):
        coach = self.get_object()
        if coach.intro_video:
            coach.delete_intro_video()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(methods=["get"], detail=False, url_path="calendar")
    def coach_calender(self, request):
        # Assuming the logged-in user is the coach
        coach = request.user.coach
        engagement_infos = EngagementInfo.objects.filter(
            coach_id=coach.id, is_chemistry_call=True
        ).select_related("coachee")
        serializer = CoachCalendarSerializer(engagement_infos, many=True)

        return Response(serializer.data)

    @action(
        methods=["get"],
        detail=False,
        url_path=r"calendar/(?P<session_date>\d{4}(?:-\d{2}(?:-\d{2})?)?)?",
    )
    def coach_calender_session_date(self, request, session_date=None):
        # Assuming the logged-in user is the coach
        coach = request.user.coach
        if len(session_date) == 10:
            engagement_infos = (
                EngagementInfo.objects.filter(
                    coach_id=coach.id,
                    is_chemistry_call=True,
                    sessions__session_date=session_date,
                    sessions__session_date__gte=datetime.now().date(),
                )
                .select_related("coachee")
                .distinct()
            )
            serializer = CoachCalendarFilterSerializer(
                engagement_infos, context={"session_date": session_date}, many=True
            )
            return Response(serializer.data)

        elif len(session_date) == 7:
            session_year, session_month = session_date.split("-")
            engagement_infos = (
                EngagementInfo.objects.filter(
                    coach_id=coach.id,
                    is_chemistry_call=True,
                    sessions__session_date__year=session_year,
                    sessions__session_date__month=session_month,
                    sessions__session_date__gte=datetime.now().date(),
                )
                .select_related("coachee")
                .distinct()
            )

            serializer = CoachCalendarFilterSerializer(
                engagement_infos,
                context={"session_year": session_year, "session_month": session_month},
                many=True,
            )
            return Response(serializer.data)
        elif len(session_date) == 4:
            session_year = session_date
            engagement_infos = (
                EngagementInfo.objects.filter(
                    coach_id=coach.id,
                    is_chemistry_call=True,
                    sessions__session_date__year=session_year,
                    sessions__session_date__gte=datetime.now().date(),
                )
                .select_related("coachee")
                .distinct()
            )

            serializer = CoachCalendarFilterSerializer(
                engagement_infos, context={"session_year": session_year}, many=True
            )
            return Response(serializer.data)

    def coach_sessions(self, request, coachee_id):
        current_date = datetime.now().date()
        if coachee_id is None:
            return Response(
                {"detail": "coachee_id parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessions = Session.objects.filter(
            engagement_info__coachee_id=coachee_id,
            engagement_info__is_assigned=True,
            call_type="Coaching Session",
            session_date__gte=current_date,
        )
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)

    def coach_students(self, request):
        coach = request.user.coach
        students = coach.engagement_infos.filter(is_assigned=True).values_list(
            "coachee_id", flat=True
        )
        coachees = (
            Coachee.objects.filter(id__in=students)
            .select_related("client")
            .order_by("client__client_name")
        )

        student_groups = {}
        for coachee in coachees:
            client_name = coachee.client.client_name
            if client_name not in student_groups:
                student_groups[client_name] = []
            student_groups[client_name].append(coachee)

        serialized_data = {}
        for client_name, coachees in student_groups.items():
            serializer = CoacheeSerializer(
                instance=coachees,
                many=True,
                context={"request": request},
            )
            serialized_data[client_name] = serializer.data

        return Response(serialized_data, status=status.HTTP_200_OK)


class FeedbackViewSet(ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["post"]

    def create(self, request):
        # Check if the user has allowed user_type
        allowed_user_types = ["Client", "Coach", "Coachee"]
        if request.user.user_type not in allowed_user_types:
            return Response(
                {"detail": "You do not have permission to send feedback."},
                status=status.HTTP_403_FORBIDDEN,
            )

        request.data["user"] = request.user.pk
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        # Set the user field to the current user
        serializer.save(user=self.request.user)


class ResponseModel():
    def __init__(self, date, start_time, end_time, is_reserved, time_zone, avail):
        self.time_zone = time_zone
        self.date = datetime.strptime(date, "%Y-%m-%d") if avail else date
        self.start_time = datetime.strptime(start_time, "%H:%M").time() if avail else start_time
        self.end_time = datetime.strptime(end_time, "%H:%M").time() if avail else end_time
        self.is_reserved = is_reserved
        self.avail = avail

    def format_date(self, date):
        return date.strftime("%Y-%m-%d")

    @property
    def to_dict(self):
        """
        Returns a dictionary containing the values of the class variables converted to the timezone defined in settings.
        """
        target_time_zone = pytz.timezone(settings.TIME_ZONE)
        if self.avail:
            combined_start_datetime = datetime.combine(self.date, self.start_time)
            combined_end_datetime = datetime.combine(self.date, self.end_time)
            offset = get_utc_offset(self.time_zone)
            converted_start_datetime, converted_end_datetime, date = convert_utc_offset(combined_start_datetime,
                                                                                        combined_end_datetime, offset)
            self.date = self.format_date(date)
        else:
            parsed_start_datetime = datetime.strptime(self.start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            parsed_end_datetime = datetime.strptime(self.end_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            parsed_start_datetime = pytz.utc.localize(parsed_start_datetime)
            parsed_end_datetime = pytz.utc.localize(parsed_end_datetime)

            offset = "+00:00"
            converted_start_datetime, converted_end_datetime, date = convert_utc_offset(
                parsed_start_datetime,
                parsed_end_datetime,
                offset
            )
            self.date = self.format_date(date)

        return {
            "date": str(self.date),
            "start_time": str(converted_start_datetime.time()),
            "end_time": str(converted_end_datetime.time()),
            "is_reserved": self.is_reserved,
            "utc_offset": get_utc_offset(settings.TIME_ZONE),
            "timezone": settings.TIME_ZONE
        }


class CoachAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = CoachAvailability.objects.all()
    serializer_class = CoachAvailabilitySerializer
    permission_classes = [IsCoachOrCoacheeUser]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.user_type == "Coach":
            return queryset.filter(
                coach=self.request.user.coach, date__gte=date.today()
            )
        else:
            return queryset.filter(date__gte=date.today())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.user_type != "Coachee":
            context["coach"] = self.request.user.coach
        return context

    # def retrieve(self, request, *args, **kwargs):
    #     coach_id = kwargs.get("coach_id")
    #     if coach_id:
    #         instances = self.get_queryset().filter(coach_id=coach_id)
    #         if instances.exists():
    #             serializer = self.get_serializer(instances, many=True)
    #             return Response(serializer.data)
    #         else:
    #             return Response(
    #                 {"detail": "Coach Availability not found."},
    #                 status=status.HTTP_404_NOT_FOUND,
    #             )

    def create_monthly_calendar(self, year, month, week_schedule, time_zone):
        monthly_calendar = []
        days_in_month = calendar.monthrange(year, month)[1]
        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day)
            weekday_name = date.strftime('%A').lower()
            response_models = []

            for day_schedule in week_schedule:
                if day_schedule['type'] == 'wday' and day_schedule['wday'] == weekday_name:
                    for interval in day_schedule['intervals']:
                        model = ResponseModel(date=date.date().isoformat(),
                                              start_time=interval['from'],
                                              end_time=interval['to'],
                                              is_reserved=False,
                                              time_zone=time_zone,
                                              avail=True
                                              )

                        monthly_calendar.append(model.to_dict)
                elif day_schedule['type'] == 'date' and day_schedule['date'] == date.strftime('%Y-%m-%d'):
                    for interval in day_schedule['intervals']:
                        model = ResponseModel(date=date.date().isoformat(),
                                              start_time=interval['from'],
                                              end_time=interval['to'],
                                              is_reserved=False,
                                              time_zone=time_zone,
                                              avail=True
                                              )
                        monthly_calendar.append(model.to_dict)

        return monthly_calendar

    def get_monthly_busy_slots(self, user, user_uri, start_date, end_date):
        current_date = start_date
        all_busy_times = []

        while current_date < end_date:
            week_end_date = current_date + timedelta(days=7)
            if week_end_date > end_date:
                week_end_date = end_date

            params = {
                "user": user_uri,
                "start_time": current_date.isoformat(),
                "end_time": week_end_date.isoformat()
            }
            weekly_busy_times = make_calendly_get_request(user, "/user_busy_times", params)
            if weekly_busy_times is not None and len(weekly_busy_times['collection']) > 0:
                for bs in weekly_busy_times['collection']:
                    event_date = datetime.fromisoformat(bs['start_time'].replace('Z', '+00:00')).date().isoformat()
                    response_model = ResponseModel(
                        date=event_date,
                        start_time=bs['start_time'],
                        end_time=bs['end_time'],
                        is_reserved=True,
                        time_zone=settings.TIME_ZONE,
                        avail=False
                    )
                    all_busy_times.append(response_model.to_dict)

            current_date = week_end_date

        return all_busy_times

    def filter_available_slots(self, avail_slots, busy_slots):
        # busy_tuples = {(bs['date']) for bs in busy_slots}
        # filtered_slots = [
        #     slot for slot in avail_slots
        #     if (slot['date']) not in busy_tuples
        # ]

        busy_tuples = {(bs['date'], bs['start_time'], bs['end_time']) for bs in busy_slots}
        filtered_slots = [
            slot for slot in avail_slots
            if (slot['date'], slot['start_time'], slot['end_time']) not in busy_tuples
        ]
        return filtered_slots

    def retrieve(self, request, *args, **kwargs):

        try:
            coach_id = kwargs.get("coach_id")
            params = request.query_params
            user_month = int(params.get('month')) if params.get('month') else None
            user_year = int(params.get('year')) if request.query_params.get('year') else None
            if not coach_id or not user_month or not user_year:
                return Response(
                    {"detail": "Invalid Perameters."}, status=status.HTTP_404_NOT_FOUND
                )
            coach = Coach.objects.filter(id=coach_id).first()
            if not coach:
                return Response(
                    {"detail": "Coach not found."}, status=status.HTTP_404_NOT_FOUND
                )
            user = coach.user
            calendely_token = CalendlyToken.objects.filter(user=user).first()
            if not calendely_token:
                return Response(
                    {"detail": "Coach is not connected to calendly."}, status=status.HTTP_404_NOT_FOUND
                )

            current_month = datetime.now().month
            current_year = datetime.now().year
            if user_year < current_year or (user_year == current_year and user_month < current_month):
                return Response(
                    {"detail": "You have entered previous month or year please enter upcoming month and year."},
                    status=status.HTTP_404_NOT_FOUND
                )

            start_date = datetime.now().date()
            current_month = start_date.month
            last_day = calendar.monthrange(start_date.year, start_date.month)[1]
            end_date = datetime(start_date.year, start_date.month, last_day).date()

            if user_month != current_month:
                last_day = calendar.monthrange(user_year, user_month)[1]
                start_date = datetime(user_year, user_month, 1).date()
                end_date = datetime(user_year, user_month, last_day).date()

            user_detail = make_calendly_get_request(coach, "/users/me")
            user_uri = user_detail["resource"]["uri"]
            if not user_detail:
                return Response(
                    {"detail": "Coach Availability not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            user_uri = user_detail["resource"]["uri"]
            params = {
                "user": user_uri
            }
            slots = make_calendly_get_request(coach, "/user_availability_schedules", params)
            default_schedule = next((item for item in slots["collection"] if item["default"]), None)
            avail_slots = self.create_monthly_calendar(user_year, user_month, default_schedule['rules'],
                                                       default_schedule['timezone'])
            busy_slots = self.get_monthly_busy_slots(coach, user_uri, start_date, end_date)
            if not avail_slots and not busy_slots:
                return Response(
                    {"detail": "Coach Availability not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            final_slots = self.filter_available_slots(avail_slots, busy_slots)

            if user_month == current_month:
                # Filter the data to remove entries with dates less than the current date
                filtered_slots = [item for item in final_slots if
                                  datetime.strptime(item['date'], '%Y-%m-%d').date() >= start_date]
                final_slots = filtered_slots

            # TODO If a coachee reserve a slot of a coach and in the next sycn the same slot is reserve by calendly
            # TODO If a coachee reserve a slot of a coach and in the next sycn the same slot is deleted
            new_slots = []
            existing_slots = []
            for slot in final_slots:
                date_str = slot["date"]
                start_time_str = slot["start_time"]
                end_time_str = slot["end_time"]
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
                end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

                availabilities = CoachAvailability.objects.filter(coach=coach, date=date, start_time=start_time,
                                                                  end_time=end_time).first()
                if availabilities:
                    if not availabilities.is_reserved:
                        existing_slots.append(availabilities.id)
                else:
                    new_slots.append(slot)

            CoachAvailability.objects.exclude(id__in=existing_slots).filter(is_reserved=False).delete()

            for availability_data in new_slots:
                date_str = availability_data["date"]
                start_time_str = availability_data["start_time"]
                end_time_str = availability_data["end_time"]
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
                end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

                availability = CoachAvailability(
                    coach=coach,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    is_reserved=availability_data["is_reserved"],
                    utc_offset=availability_data["utc_offset"]
                )

                availability.save()

            for item in final_slots:
                start_time_obj = datetime.strptime(item["start_time"], "%H:%M:%S").strftime("%I:%M%p")
                item["start_time"] = start_time_obj

                end_time_obj = datetime.strptime(item["end_time"], "%H:%M:%S").strftime("%I:%M%p")
                item["end_time"] = end_time_obj

            month_availabilities = CoachAvailability.objects.filter(coach=coach, date__year=user_year,
                                                                    date__month=user_month)
            serializer = CoachAvailabilitySerializer(instance=month_availabilities, many=True)

            serialized_data = serializer.data
            return Response(serialized_data)

        except:
            return Response(
                {"detail": "Something went wrong."}, status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        instance = self.get_object()
        obj = CoachAvailability.objects.filter(id=pk)
        if obj.exists():
            if obj.first().is_reserved:
                return Response({"detail": "Slot is reserved so you cannot change it."})
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=False)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            else:
                if "non_field_errors" in serializer.errors:
                    return Response(
                        {"detail": serializer.errors["non_field_errors"][0]}
                    )
                return Response(serializer.errors)
        except:
            return Response({"detail": "Something went wrong"})

    def partial_update(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        instance = self.get_object()
        obj = CoachAvailability.objects.filter(id=pk)
        if obj.exists():
            if obj.first().is_reserved:
                return Response({"detail": "Slot is reserved so you cannot change it."})
        try:
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            else:
                if "non_field_errors" in serializer.errors:
                    return Response(
                        {"detail": serializer.errors["non_field_errors"][0]}
                    )
                return Response(serializer.errors)
        except:
            return Response({"detail": "Something went wrong"})

    def get_permissions(self):
        if self.action == "retrieve" and "coach_id" in self.kwargs:
            permission_classes = [IsCoachOrCoacheeUser]
        else:
            permission_classes = self.permission_classes

        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            date = serializer.validated_data.get("date")
            start_time = serializer.validated_data.get("start_time")
            end_time = serializer.validated_data.get("end_time")
            coach = self.request.user.coach
            current_time = datetime.now().time()
            current_date = date.today()

            if coach and date and start_time and end_time:
                existing_coach_availability = CoachAvailability.objects.filter(
                    coach=coach, date=date, start_time=start_time, end_time=end_time
                ).exists()

                if existing_coach_availability:
                    return Response(
                        {"detail": "Slot with the same details already exists."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            if start_time and end_time:
                if start_time >= end_time:
                    return Response(
                        {"detail": "Start time must be earlier than end time."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            if date < current_date or (
                    date == current_date
                    and (start_time < current_time or end_time < current_time)
            ):
                return Response(
                    {
                        "detail": "You have entered previous date or time please enter upcoming date and time."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Count the existing timeslots for the selected date
            existing_timeslots_count = CoachAvailability.objects.filter(
                coach=coach, date=date
            ).count()

            if existing_timeslots_count >= 6:
                return Response(
                    {"detail": "You cannot add more than 6 timeslots in one date."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer.save(coach=coach)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )
        else:
            if "non_field_errors" in serializer.errors:
                return Response(
                    {"detail": serializer.errors["non_field_errors"][0]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CalendlyViewSet(viewsets.ViewSet):
    permission_classes = [IsCoachOrCoacheeUser]

    @action(detail=False, permission_classes=[IsCoachUser])
    def deactivate(self, request):
        calendly_token = CalendlyToken.objects.filter(user=request.user).first()
        if calendly_token:
            calendly_token.delete()
            return Response({"detail": "User successfully deactivated from Calendly."}, status=status.HTTP_200_OK)
        return Response({"detail": "User is not connected to Calendly."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["get"])
    def list(self, request, coach_id):
        try:
            start_time = request.GET.get("start_time")
            end_time = request.GET.get("end_time")
            if not start_time or not end_time:
                return Response(
                    {"detail": "Missing parameters."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            coach = Coach.objects.filter(id=coach_id).first()
            if not coach:
                return Response(
                    {"detail": "Coach not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            user_detail = make_calendly_get_request(coach, "/users/me")
            if not user_detail:
                return Response(
                    {"detail": "Coach Availability not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            user_uri = user_detail["resource"]["uri"]
            params = {
                "user": user_uri
            }
            slots = make_calendly_get_request(coach, "/user_availability_schedules", params)
            default_schedule = next((item for item in slots["collection"] if item["default"]), None)
            params = {
                "user": user_uri,
                "start_time": start_time,
                "end_time": end_time
            }
            busy_slots = make_calendly_get_request(coach, "/user_busy_times", params)
            if not slots or not default_schedule:
                return Response(
                    {"detail": "Coach Availability not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {
                    'week_schedule': default_schedule['rules'],
                    'busy_slots': busy_slots['collection']
                },
                status=status.HTTP_200_OK
            )
        except:
            return Response(
                {"detail": "Something went wrong."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CoachAvailabilityListViewSet(viewsets.ModelViewSet):
    queryset = CoachAvailability.objects.all()
    serializer_class = CoachAvailabilityListSerializer
    permission_classes = [IsCoachUser]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.user_type == "Coach":
            return queryset.filter(
                coach=self.request.user.coach, date__gte=date.today()
            )
        else:
            return queryset.filter(date__gte=date.today())

    def conflicting_handling(self, date, start_time, end_time, item_ids=None):
        if item_ids is not None:
            start_time_conflicting_slots = (
                CoachAvailability.objects.filter(coach=self.request.user.coach)
                .filter(date=date)
                .filter(start_time__lte=start_time)
                .filter(end_time__gt=start_time)
                .exclude(id__in=item_ids)
            )
            end_time_conflicting_slots = (
                CoachAvailability.objects.filter(coach=self.request.user.coach)
                .filter(date=date)
                .filter(start_time__lte=end_time)
                .filter(end_time__gt=end_time)
                .exclude(id__in=item_ids)
            )
        else:
            start_time_conflicting_slots = (
                CoachAvailability.objects.filter(coach=self.request.user.coach)
                .filter(date=date)
                .filter(start_time__lte=start_time)
                .filter(end_time__gt=start_time)
            )
            end_time_conflicting_slots = (
                CoachAvailability.objects.filter(coach=self.request.user.coach)
                .filter(date=date)
                .filter(start_time__lte=end_time)
                .filter(end_time__gt=end_time)
            )
        if start_time_conflicting_slots.exists() or end_time_conflicting_slots.exists():
            return True
        return False

    def has_conflict(self, slots, new_slot):
        for existing_slot in slots:
            if existing_slot["date"] == new_slot["date"]:
                start_time_of_existing = existing_slot["start_time"]
                end_time_of_existing = existing_slot["end_time"]
                start_time_of_new_slot = new_slot["start_time"]
                end_time_of_new_slot = new_slot["end_time"]

                if (start_time_of_existing != start_time_of_new_slot) or (
                        end_time_of_existing != end_time_of_new_slot
                ):
                    if (start_time_of_existing < start_time_of_new_slot) and (
                            start_time_of_new_slot < end_time_of_existing
                    ):
                        return True
                    elif (start_time_of_existing < end_time_of_new_slot) and (
                            end_time_of_new_slot < end_time_of_existing
                    ):
                        return True
        return False

    def get_serializer_class(self):
        if isinstance(self.request.data, list):
            return CoachAvailabilityListSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action == "retrieve" and "coach_id" in self.kwargs:
            permission_classes = [IsCoachOrCoacheeUser]
        else:
            permission_classes = self.permission_classes

        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["post"])
    def bulk_create_or_update(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            return Response(
                {"detail": "Data should be provided in a list format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            data=request.data, many=isinstance(request.data, list)
        )
        serializer.is_valid(raise_exception=True)
        coach = self.request.user.coach
        current_time = datetime.now().time()
        current_date = datetime.now().date()

        unique_data = set()  # Initialize set to store unique slot data

        time_slots = []
        existing_slots = []
        duplicate_data = []
        updated_slots = []
        conflicting_slots = []
        ids_of_updated_slots = []

        for i in serializer.validated_data:
            if "id" in i:
                ids_of_updated_slots.append(i.get("id"))

        for item in serializer.validated_data:
            error_message = {
                "detail": "Slots cannot overlap. Please choose a time that doesn't conflict with existing slots"
            }
            # checking the conflition between the given slots
            for new_slot in serializer.validated_data:
                if self.has_conflict(conflicting_slots, new_slot):
                    return Response(error_message, status=status.HTTP_400_BAD_REQUEST)
                conflicting_slots.append(new_slot)

            # checking confliction between already exits slots of coach
            if "id" in item:
                response = self.conflicting_handling(
                    item.get("date"),
                    item.get("start_time"),
                    item.get("end_time"),
                    item_ids=ids_of_updated_slots,
                )
            else:
                response = self.conflicting_handling(
                    item.get("date"), item.get("start_time"), item.get("end_time")
                )
            if response:
                return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

            if "id" in item:
                instance = CoachAvailability.objects.filter(
                    id=item["id"], coach=coach
                ).first()
                if instance:
                    if instance.is_reserved:
                        return Response(
                            {
                                "detail": f"Slot having id {instance.id} is reserved so you cannot change it."
                            }
                        )
                    date = item.get("date")
                    start_time = item.get("start_time")
                    end_time = item.get("end_time")
                    slot_data = (date, start_time, end_time)

                    if coach and date and start_time and end_time:
                        if start_time >= end_time:
                            return Response(
                                {"detail": "Start time must be earlier than end time."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        if date < current_date or (
                                date == current_date
                                and (start_time < current_time or end_time < current_time)
                        ):
                            return Response(
                                {
                                    "detail": "You have entered a previous date or time. Please enter an upcoming date and time."
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        existing_coach_availability = (
                            CoachAvailability.objects.filter(
                                coach=coach,
                                date=date,
                                start_time=start_time,
                                end_time=end_time,
                            )
                            .exclude(id=instance.id)
                            .exists()
                        )

                        if existing_coach_availability:
                            existing_slots.append(
                                {
                                    "date": date,
                                    "start_time": start_time.strftime("%I:%M%p"),
                                    "end_time": end_time.strftime("%I:%M%p"),
                                }
                            )
                        elif slot_data == (
                                instance.date,
                                instance.start_time,
                                instance.end_time,
                        ):
                            duplicate_data.append(
                                {
                                    "date": date,
                                    "start_time": start_time.strftime("%I:%M%p"),
                                    "end_time": end_time.strftime("%I:%M%p"),
                                }
                            )
                        else:
                            instance.date = date
                            instance.start_time = start_time
                            instance.end_time = end_time
                            instance.utc_offset = get_utc_offset(settings.TIME_ZONE)
                            instance.save()
                            updated_slots.append(instance)
            else:
                date = item.get("date")
                start_time = item.get("start_time")
                end_time = item.get("end_time")
                slot_data = (date, start_time, end_time)

                if coach and date and start_time and end_time:
                    existing_coach_availability = CoachAvailability.objects.filter(
                        coach=coach, date=date, start_time=start_time, end_time=end_time
                    ).exists()

                    if existing_coach_availability:
                        existing_slots.append(
                            {
                                "date": date,
                                "start_time": start_time.strftime("%I:%M%p"),
                                "end_time": end_time.strftime("%I:%M%p"),
                            }
                        )
                    elif slot_data in unique_data:
                        duplicate_data.append(
                            {
                                "date": date,
                                "start_time": start_time.strftime("%I:%M%p"),
                                "end_time": end_time.strftime("%I:%M%p"),
                            }
                        )
                    else:
                        if start_time >= end_time:
                            return Response(
                                {"detail": "Start time must be earlier than end time."},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        if date < current_date or (
                                date == current_date
                                and (start_time < current_time or end_time < current_time)
                        ):
                            return Response(
                                {
                                    "detail": "You have entered a previous date or time. Please enter an upcoming date and time."
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        unique_data.add(slot_data)
                        time_slot = CoachAvailability(
                            coach=coach,
                            date=date,
                            start_time=start_time,
                            end_time=end_time,
                            utc_offset=get_utc_offset(settings.TIME_ZONE),
                        )
                        time_slots.append(time_slot)

        if existing_slots:
            return Response(
                {
                    "detail": "Slot with the same details already exists.",
                    "existing_slots": existing_slots,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if adding the time slots will exceed the limit of 6 slots in one date
        existing_timeslots_count = CoachAvailability.objects.filter(
            coach=coach, date__in=[slot.date for slot in time_slots]
        ).count()

        if existing_timeslots_count + len(time_slots) > 6:
            return Response(
                {"detail": "You cannot add more than 6 timeslots in one date."},
                status=status.HTTP_403_FORBIDDEN,
            )

        CoachAvailability.objects.bulk_create(time_slots)
        serialized_instances = self.get_serializer(time_slots, many=True)

        if duplicate_data and not time_slots:
            return Response(
                {
                    "detail": "Records have duplicate data.",
                    "duplicate_data": duplicate_data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif duplicate_data:
            return Response(
                {
                    "detail": "One record saved. Other records have duplicate data.",
                    "duplicate_data": duplicate_data,
                },
                status=status.HTTP_201_CREATED,
            )
        elif updated_slots and time_slots:
            updated_serialized_instances = self.get_serializer(updated_slots, many=True)
            return Response(
                updated_serialized_instances.data + serialized_instances.data,
                status=status.HTTP_201_CREATED,
            )

        elif updated_slots:
            updated_serialized_instances = self.get_serializer(updated_slots, many=True)
            return Response(
                updated_serialized_instances.data,
                status=status.HTTP_200_OK,
            )
        elif time_slots:
            return Response(
                serialized_instances.data,
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"detail": "No slots were created or updated."},
                status=status.HTTP_200_OK,
            )


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsCoacheeUser]

    def create(self, request, engagement_info_id, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        engagement_info = EngagementInfo.objects.get(id=engagement_info_id)
        coach_id = engagement_info.coach_id
        session_date = serializer.validated_data.get("session_date")
        start_time = serializer.validated_data.get("start_time")
        end_time = serializer.validated_data.get("end_time")
        call_type = serializer.validated_data.get("call_type")
        utc_offset = serializer.validated_data.get("utc_offset")
        local_start_time = request.data["start_time"]
        local_end_time = request.data["end_time"]
        local_date = request.data["session_date"]

        if (
                engagement_info_id
                and session_date
                and start_time
                and end_time
                and call_type
        ):
            existing_session = Session.objects.filter(
                engagement_info_id=engagement_info_id,
                session_date=session_date,
                start_time=start_time,
                end_time=end_time,
                call_type=call_type,
            ).exists()

            if existing_session:
                return Response(
                    {"detail": "Session with the same details already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if start_time and end_time:
            if start_time >= end_time:
                return Response(
                    {"detail": "Start time must be earlier than end time."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if call_type == "Chemistry Call":
            existing_chemistry_call = Session.objects.filter(
                engagement_info=engagement_info, call_type="Chemistry Call"
            ).exists()

            if existing_chemistry_call:
                return Response(
                    {
                        "detail": "You have already scheduled a chemistry call with this coach."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif call_type == "Coaching Session":
            existing_chemistry_call = Session.objects.filter(
                engagement_info=engagement_info, call_type="Chemistry Call"
            ).exists()

            if not existing_chemistry_call:
                return Response(
                    {
                        "detail": "You can only schedule a coaching session if you have already scheduled a chemistry call with this coach."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        coachee_id = request.user.coachee.id
        if engagement_info.coachee_id != coachee_id:
            return Response(
                {
                    "detail": "You are not authorized to schedule a session for this engagement."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        time_slots = CoachAvailability.objects.filter(
            coach_id=coach_id,
            date=session_date,
            start_time=start_time,
            end_time=end_time,
            is_reserved=False,
        )
        if not time_slots.exists():
            return Response(
                {"detail": "This time slot is not available for this coach."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            coachee_email = engagement_info.coachee.email
            coach_email = engagement_info.coach.email
            coach_name = (
                f"{engagement_info.coach.first_name} {engagement_info.coach.last_name}"
            )
            coachee_name = f"{engagement_info.coachee.first_name} {engagement_info.coachee.last_name}"

            # TODO this timezone needs to verify on production
            timezone_name = settings.TIME_ZONE
            timezone_obj = pytz.timezone(timezone_name)

            if call_type == "Chemistry Call":
                engagement_info.is_chemistry_call = True

            elif call_type == "Coaching Session":
                if engagement_info.is_chemistry_call and engagement_info.is_assigned:
                    if (
                            engagement_info.coachee.num_sessions
                            == engagement_info.num_scheduled_sessions
                    ):
                        return Response(
                            {"detail": "You have reached your sessions limit."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    engagement_info.num_scheduled_sessions += 1
                else:
                    return Response(
                        {
                            "detail": "You cannot create a coaching session until you have scheduled a chemistry call and select a coach."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            # TODO this code is to create ics events, it may need in future if client enhance functionality.
            # # Create the iCalendar event
            # event = Event()
            # event.add("summary", call_type)
            # event.add("dtstart", start_datetime)
            # event.add("dtend", end_datetime)
            # # Set the organizer information
            # organizer = vCalAddress("MAILTO:" + coachee_email)
            # organizer.params["cn"] = coachee_email
            # event["organizer"] = organizer
            #
            # # Create the iCalendar file (Calendar) and add the event
            # cal = Calendar()
            # cal.add_component(event)
            # ics_content = cal.to_ical().decode("utf-8")

            start_datetime_str = start_time.strftime("%m/%d/%Y")
            start_time_str = start_time.strftime("%I:%M %p")
            end_time_str = end_time.strftime("%I:%M %p")

            local_date = datetime.strptime(str(local_date), "%Y-%m-%d")
            local_start_time = datetime.strptime(str(local_start_time), "%I:%M%p")
            local_end_time = datetime.strptime(str(local_end_time), "%I:%M%p")

            # Format the date and times in the desired format
            start_date_time_formatted = local_date.strftime("%m/%d/%Y")
            start_time_formatted = local_start_time.strftime("%I:%M %p")
            end_time_formatted = local_end_time.strftime("%I:%M %p")

            coachee_context = {
                "call_type_name": call_type.lower(),
                "name": coachee_name,
                "date": start_date_time_formatted,
                "start_time": start_time_formatted,
                "end_time": end_time_formatted,
            }
            coach_context = {
                "call_type_name": call_type.lower(),
                "name": coach_name,
                "date": start_date_time_formatted,
                "start_time": start_time_formatted,
                "end_time": end_time_formatted,
            }

            html = "session_email.html"
            html_content_coachee = render_to_string(html, coachee_context)
            html_content_coach = render_to_string(html, coach_context)

            subject = f"[Sloan Leaders] {call_type} Scheduled"
            # TODO this code is to create ics events, it may need in future if client enhance functionality.
            # send_invitation(coachee_email, subject, html_content, ics_content)
            # send_invitation(coach_email, subject, html_content, ics_content)
            coachee_response = send_email(coachee_email, subject, html_content_coach)
            coach_response = send_email(coach_email, subject, html_content_coachee)
            if not coachee_response and not coach_response:
                # If email sending fails, delete the user object
                transaction.set_rollback(True)
                raise serializers.ValidationError(
                    {"detail": "Email could not be sent. Coachee not created."}
                )
            # Update time slot for coach to make it reserve
            if time_slots.exists():
                time_slots.update(is_reserved=True)
            engagement_info.save()
            session_obj = serializer.save(engagement_info=engagement_info)

            # This import should keep here, otherwise apscheduler could not trigger the job
            from calm_darkness_38642.schedular import (
                schedule_session_notifications,
                notifications,
            )

            # kwargs for scheduled notification fucntion
            kwargs = {
                "action_type": "coachee_review",
                "profile_picture": str(engagement_info.coachee.profile_picture.url)
                if engagement_info.coachee.profile_picture
                else "",
                "notification_name": f"Please provide feedback from the Coaching Session with {engagement_info.coachee.first_name} {engagement_info.coachee.last_name}",
                "notification_text": engagement_info.coachee.first_name
                                     + " "
                                     + engagement_info.coachee.last_name
                                     + " review",
                "coach_id": engagement_info.coach.id,
                "coachee_id": engagement_info.coachee.id,
                "engagement_info_id": engagement_info_id,
                "session_id": session_obj.id,
            }

            schedular_session_date = (
                    end_time.strftime("%Y-%m-%d %H:%M:%S") + utc_offset
            )

            coach_object = Coach.objects.filter(id=coach_id)
            coachee_id = engagement_info.coachee.id
            session_id = session_obj.id

            history_data = {
                "coach_id": coach_id,
                "coachee_id": coachee_id,
                "engagement_info_id": engagement_info_id,
                "session_id": session_id,
                "profile_picture": None,
            }

            fcm_data = {
                "coach_id": str(coach_id),
                "coachee_id": str(coachee_id),
                "engagement_info_id": str(engagement_info_id),
                "session_id": str(session_id),
            }

            if call_type == "Coaching Session":
                # schedule a notification for session review
                schedule_session_notifications(
                    schedule=end_time, kwargs=kwargs
                )

                # sending notification to the coach after scheduling a session from coachee

                notification_name = (
                        engagement_info.coachee.first_name
                        + " "
                        + engagement_info.coachee.last_name
                        + ", "
                        + str(
                    datetime.strptime(str(session_date), "%Y-%m-%d").strftime(
                        "%B %d, %Y"
                    )
                )
                        + " "
                        + start_time_str
                        + " - "
                        + end_time_str
                        + " EST"
                )
                notification_text = "Coaching session"
                action_type = "coaching_session"
                fcm_data["action_type"] = str(action_type)

                if settings.BACKGROUND_TASK_EXECUTED == False:
                    process_tasks_cmd = "python manage.py process_tasks"
                    process_tasks_args = shlex.split(process_tasks_cmd)
                    subprocess.Popen(process_tasks_args)
                    settings.BACKGROUND_TASK_EXECUTED = True

            if call_type == "Chemistry Call":
                notification_name = (
                        engagement_info.coachee.first_name
                        + " "
                        + engagement_info.coachee.last_name
                        + ", "
                        + str(
                    datetime.strptime(str(session_date), "%Y-%m-%d").strftime(
                        "%B %d, %Y"
                    )
                )
                        + " "
                        + start_time_str
                        + " - "
                        + end_time_str
                        + " EST"
                )
                notification_text = "Chemistry call"
                action_type = "chemistry_call"
                fcm_data["action_type"] = str(action_type)

            notifications(
                action_type=action_type,
                user_id=coach_object.first().user_id if coach_object.exists() else None,
                notification_name=notification_name,
                notification_text=notification_text,
                profile_picture=str(engagement_info.coachee.profile_picture.url)
                if engagement_info.coachee.profile_picture
                else "",
                fcm_data=fcm_data,
                history_data=history_data,
            )
            return Response(
                {"detail": f"{call_type} Scheduled Successfully."},
                status=status.HTTP_201_CREATED,
            )

    def retrieve(self, request, engagement_info_id, *args, **kwargs):
        engagement_info = EngagementInfo.objects.get(id=engagement_info_id)
        coachee_id = engagement_info.coachee_id
        coachee = request.user.coachee
        if coachee_id:
            instances = EngagementInfo.objects.filter(
                coachee_id=coachee_id, is_assigned=True
            )
            if instances.exists():
                return Response(
                    {"detail": "You have already selected a coach."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif (
                    engagement_info.is_chemistry_call == True
                    and engagement_info.coachee == coachee
            ):
                engagement_info.is_assigned = True
                coachee.engagement_status = "Start Engagement"
                engagement_info.start_date = datetime.now()
                engagement_info.save()
                coachee.save()

                history_data = {
                    "coach_id": engagement_info.coach.id,
                    "coachee_id": engagement_info.coachee.id,
                    "engagement_info_id": engagement_info_id,
                    "profile_picture": None,
                }

                fcm_data = {
                    "coach_id": str(engagement_info.coach.id),
                    "coachee_id": str(engagement_info.coachee.id),
                    "engagement_info_id": str(engagement_info_id),
                }
                notifications(
                    action_type="coach_selection",
                    user_id=engagement_info.coach.user_id,
                    notification_name=f"{coachee.first_name} {coachee.last_name} has selected you to be their Executive Coach!",
                    notification_text=f"{engagement_info.coachee.first_name} {engagement_info.coachee.last_name}",
                    profile_picture=str(engagement_info.coachee.profile_picture.url)
                    if engagement_info.coachee.profile_picture
                    else "",
                    fcm_data=fcm_data,
                    history_data=history_data,
                )
                return Response(
                    {"detail": "Coach selected successfully"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        "detail": "You cannot select the coach because your chemistry call is not scheduled with this coach."
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            return Response(
                {"detail": "Operation failed."}, status=status.HTTP_403_FORBIDDEN
            )


class CoachReviewsViewSet(viewsets.ViewSet):
    serializer_class = CoachReviewsSerializer
    permission_classes = [IsCoachUser]

    @action(detail=False, methods=["post"])
    def create(self, request, session_id):
        serializer = self.serializer_class(
            data=request.data, context={"session_id": session_id}
        )
        if serializer.is_valid():
            obj = CoachReviews(
                session_id=session_id,
                rate=serializer.data.get("rate"),
                comment=serializer.data.get("comment")
                if serializer.data.get("comment") is not None
                else " ",
            )
            obj.save()
            return Response(
                {"detail": "Review submitted."},
                status=status.HTTP_200_OK,
            )
        else:
            error_field = next(iter(serializer.errors))
            errors = serializer.errors[error_field]
            return Response(
                {"detail": errors[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def retrieve(self, request, session_id):
        try:
            try:
                session_obj = Session.objects.get(id=session_id)
            except:
                return Response({"detail": "Invalid session id."})
            obj = CoachReviews.objects.get(session_id=session_id)
            return Response({"rate": obj.rate, "comment": obj.comment})
        except:
            return Response({"detail": "Review not found."})


class CoacheeReviewsViewSet(viewsets.ViewSet):
    serializer_class = CoacheesReviewsSerializer
    permission_classes = [IsCoacheeUser]

    @action(detail=False, methods=["post"])
    def create(self, request, session_id):
        serializer = self.serializer_class(
            data=request.data, context={"session_id": session_id}
        )
        if serializer.is_valid():
            obj = CoacheesReviews(
                session_id=session_id,
                rate_1=serializer.data.get("rate_1"),
                comment=serializer.data.get("comment")
                if serializer.data.get("comment") is not None
                else " ",
            )
            obj.save()
            # sending Notification to client
            session_obj = Session.objects.filter(id=session_id)
            if session_obj.exists():
                so = session_obj.first()
                so.is_reviewed_by_coachee = True
                so.save()

                action_type = "coachee_review_for_client"
                engagement_info_object = session_obj.first().engagement_info
                clientUserID = engagement_info_object.coachee.client.user_id
                coach = engagement_info_object.coach
                coachee = engagement_info_object.coachee
                notification_name = f"{coachee.first_name} {coachee.last_name} left a review for their Coaching Session."
                notification_text = ""

                profile_picture = (
                    str(engagement_info_object.coachee.profile_picture.url)
                    if engagement_info_object.coachee.profile_picture
                    else "",
                )
                fcm_data = {
                    "action_type": action_type,
                    "coach_id": str(coach.id),
                    "coachee_id": str(coachee.id),
                    "engagement_info_id": str(engagement_info_object.id),
                }
                history_data = {
                    "coach_id": coach.id,
                    "coachee_id": coachee.id,
                    "engagement_info_id": engagement_info_object.id,
                    "profile_picture": None,
                }

                notifications(
                    action_type=action_type,
                    user_id=clientUserID,
                    notification_name=notification_name,
                    notification_text=notification_text,
                    fcm_data=fcm_data,
                    history_data=history_data,
                    profile_picture=profile_picture,
                )

            return Response(
                {"detail": "Review submitted."},
                status=status.HTTP_200_OK,
            )
        else:
            error_field = next(iter(serializer.errors))
            errors = serializer.errors[error_field]
            return Response(
                {"detail": errors[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def retrieve(self, request, session_id):
        try:
            try:
                session_obj = Session.objects.get(id=session_id)
            except:
                return Response({"detail": "Invalid session id."})
            obj = CoacheesReviews.objects.get(session_id=session_id)
            return Response(
                {
                    "rate_1": obj.rate_1,
                    "comment": obj.comment,
                }
            )
        except:
            return Response({"detail": "Review not found."})


class DeviceRegistration(viewsets.ViewSet):
    """
    In this we add/registed device in FCMDevice
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"])
    def create(self, request, device_token):
        try:
            user_obj = request.user
            device_obj = FCMDevice.objects.filter(
                Q(user=user_obj) & Q(registration_id=device_token)
            )
            if device_obj.exists():
                return Response("Device with this device_id Already Exists")
            else:
                FCMDevice.objects.create(user=user_obj, registration_id=device_token)
                return Response({"detail": "Device Registered."})
        except:
            return Response({"detail": "User does not exist."})


class CoachFinalReportViewSet(viewsets.ViewSet):
    serializer_class = FinalReportReviewSerializer
    permission_classes = [IsCoachUser]

    @action(detail=False, methods=["post"])
    def create(self, request, engagement_id):
        # creating coach final report
        serializer = self.serializer_class(
            data=request.data,
            context={"engagement_id": engagement_id, "user_type": "coach"},
        )
        if serializer.is_valid():
            CoachFinalReportReview.objects.create(
                engagement_info_id=engagement_id,
                rate_1=serializer.data.get("rate_1"),
                rate_2=serializer.data.get("rate_2"),
                rate_3=serializer.data.get("rate_3"),
                rate_4=serializer.data.get("rate_4"),
                comment=serializer.data.get("comment")
                if serializer.data.get("comment")
                else " ",
            )
            return Response(
                {"detail": "Review submitted."},
                status=status.HTTP_200_OK,
            )
        else:
            error_field = next(iter(serializer.errors))
            errors = serializer.errors[error_field]
            return Response(
                {"detail": errors[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def retrieve(self, request, engagement_id):
        try:
            try:
                engagment_obj = EngagementInfo.objects.get(id=engagement_id)
            except:
                return Response({"detail": "Invalid engagment id."})
            obj = CoachFinalReportReview.objects.get(engagement_info_id=engagement_id)
            return Response(
                {
                    "rate_1": obj.rate_1,
                    "rate_2": obj.rate_2,
                    "rate_3": obj.rate_3,
                    "rate_4": obj.rate_4,
                    "comment": obj.comment,
                }
            )
        except:
            return Response({"detail": "Review not found."})


class CoacheeFinalReportViewSet(viewsets.ViewSet):
    serializer_class = FinalReportReviewSerializer
    permission_classes = [IsCoacheeUser]

    @action(detail=False, methods=["post"])
    def create(self, request, engagement_id):
        serializer = self.serializer_class(
            data=request.data,
            context={"engagement_id": engagement_id, "user_type": "coachee"},
        )
        if serializer.is_valid():
            CoacheesFinalReportReview.objects.create(
                engagement_info_id=engagement_id,
                rate_1=serializer.data.get("rate_1"),
                rate_2=serializer.data.get("rate_2"),
                rate_3=serializer.data.get("rate_3"),
                rate_4=serializer.data.get("rate_4"),
                comment=serializer.data.get("comment")
                if serializer.data.get("comment")
                else " ",
            )
            # Sending Notification to client to inform that the coachee has submitted his final report review
            engagement_info_object = EngagementInfo.objects.filter(id=engagement_id)
            if engagement_info_object.exists():
                action_type = "coachee_final_report_review_for_client"
                engagement_info_object = engagement_info_object.first()
                client_userID = engagement_info_object.coachee.client.user_id
                coach = engagement_info_object.coach
                coachee = engagement_info_object.coachee
                notification_name = f"{coachee.first_name} {coachee.last_name} submitted a Final Report."
                notification_text = ""

                profile_picture = (
                    str(engagement_info_object.coachee.profile_picture.url)
                    if engagement_info_object.coachee.profile_picture
                    else "",
                )
                fcm_data = {
                    "action_type": action_type,
                    "coach_id": coach.id,
                    "coachee_id": coachee.id,
                    "engagement_info_id": engagement_id,
                }
                history_data = {
                    "coach_id": coach.id,
                    "coachee_id": coachee.id,
                    "engagement_info_id": engagement_id,
                    "profile_picture": None,
                }

                notifications(
                    action_type=action_type,
                    user_id=client_userID,
                    notification_name=notification_name,
                    notification_text=notification_text,
                    fcm_data=fcm_data,
                    history_data=history_data,
                    profile_picture=profile_picture,
                )

            return Response(
                {"detail": "Review submitted."},
                status=status.HTTP_200_OK,
            )
        else:
            error_field = next(iter(serializer.errors))
            errors = serializer.errors[error_field]
            return Response(
                {"detail": errors[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def retrieve(self, request, engagement_id):
        try:
            try:
                engagment_obj = EngagementInfo.objects.get(id=engagement_id)
            except:
                return Response({"detail": "Invalid engagment id."})
            obj = CoacheesFinalReportReview.objects.get(
                engagement_info_id=engagement_id
            )
            return Response(
                {
                    "rate_1": obj.rate_1,
                    "rate_2": obj.rate_2,
                    "rate_3": obj.rate_3,
                    "rate_4": obj.rate_4,
                    "comment": obj.comment,
                }
            )
        except:
            return Response({"detail": "Review not found."})


class NotificationHistoryViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationHistorySerializer

    @action(detail=False, methods=["get"])
    def list(self, request):
        current_user = request.user
        history = NotificationHistory.objects.filter(user=current_user)
        for noti in history:
            if "profile_picture" in noti.data:
                if (
                        current_user.user_type == "Coach"
                        or current_user.user_type == "Client"
                ):
                    coachee_obj = Coachee.objects.filter(
                        id=noti.data["coachee_id"]
                    ).first()
                    noti.data["profile_picture"] = (
                        (
                            coachee_obj.get_profile_picture_url()
                            if coachee_obj.profile_picture
                            else ""
                        )
                        if coachee_obj
                        else ""
                    )

                    noti.save()

                elif current_user.user_type == "Coachee":
                    coach_obj = Coach.objects.filter(id=noti.data["coach_id"]).first()
                    noti.data["profile_picture"] = (
                        (
                            coach_obj.get_profile_picture_url()
                            if coach_obj.profile_picture
                            else ""
                        )
                        if coach_obj
                        else ""
                    )

                    noti.save()
        serializer = self.serializer_class(instance=history, many=True)
        return Response(serializer.data)


class SingleNotificationReaderViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["patch"])
    def partial_update(self, request, notification_id, pk=None):
        noti = NotificationHistory.objects.filter(id=notification_id).first()
        if noti is not None:
            noti.is_read = True
            noti.save()
            return Response({"detail": "Notification readed."})
        else:
            return Response({"detail": "Invalid notification id."})


class AllNotificationsReaderViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["patch"])
    def partial_update(self, request, pk=None):
        current_user = request.user
        all_notifications = NotificationHistory.objects.filter(
            user=current_user, is_read=False
        )
        if all_notifications.exists():
            for noti in all_notifications:
                noti.is_read = True
                noti.save()
            else:
                return Response({"detail": "All notification readed."})
        else:
            return Response({"detail": "Notifications not found."})


class SessionDetailViewSet(viewsets.ViewSet):
    permission_classes = [IsCoachOrCoacheeUser]

    @action(detail=False, methods=["get"])
    def retrieve(self, request, session_id):
        session_obj = Session.objects.filter(
            id=session_id, call_type="Coaching Session"
        )
        if session_obj.exists():
            session_obj = session_obj.first()
            session_data = {
                "engagement_info": session_obj.engagement_info_id,
                "session_date": session_obj.session_date,
                "start_time": session_obj.start_time,
                "end_time": session_obj.end_time,
                "call_type": session_obj.call_type,
                "timezone": settings.TIME_ZONE,
                "is_notify": session_obj.is_notify,
                "is_reviewed_by_coach": session_obj.is_reviewed_by_coach,
                "is_reviewed_by_coachee": session_obj.is_reviewed_by_coachee,
            }
            return Response(session_data)
        else:
            return Response({"detail": "Invalid Session Id."})


class ClientCoachesViewSet(viewsets.ViewSet):
    """
    This will return the coachees whose engagement status is not Pending
    """

    permission_classes = [IsClientUser]
    serializer_class = CoachSerializer

    @action(detail=False, methods=["get"])
    def list(self, request):
        client_obj = Client.objects.get(user=request.user)
        objs = EngagementInfo.objects.filter(
            coachee__client=client_obj, is_chemistry_call=True, is_assigned=True
        )
        coaches_ids_list = objs.values_list("coach", flat=True).distinct()
        coaches = Coach.objects.filter(id__in=coaches_ids_list).distinct()
        serializer = self.serializer_class(coaches, many=True)
        return Response(list(serializer.data))


class ClientCoacheeSessionsViewSet(viewsets.ViewSet):
    """
    This will return all the session detail of a particular engagement id
    """

    permission_classes = [IsClientUser]
    serializer_class = SessionSerializer

    @action(detail=False, methods=["get"])
    def list(self, request, engagement_info_id):
        try:
            engagment_obj = EngagementInfo.objects.get(
                id=engagement_info_id, is_chemistry_call=True, is_assigned=True
            )
        except:
            return Response(
                {"detail": "invalid engagement info id."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sessions_objs = Session.objects.filter(
            engagement_info_id=engagement_info_id, call_type="Coaching Session"
        )
        serializer = self.serializer_class(sessions_objs, many=True)
        return Response(list(serializer.data))


class ClientCoacheeEngagementDetailViewSet(viewsets.ViewSet):
    """
    This will return the engagement detail of a coachee
    and a flag which tell that all the sessions completed or not to show the final report on the client portel
    """

    permission_classes = [IsClientUser]
    serializer_class = ClientCoacheeEngagementDetailSerializer

    @action(detail=False, methods=["get"])
    def list(self, request, coachee_id):
        try:
            coachee_obj = Coachee.objects.get(id=coachee_id)
        except:
            return Response(
                {"detail": "invalid coachee id."}, status=status.HTTP_404_NOT_FOUND
            )

        objs = EngagementInfo.objects.filter(
            coachee_id=coachee_id, is_chemistry_call=True, is_assigned=True
        )

        if objs.exists():
            serializers = self.serializer_class(objs.first())
            response = serializers.data
            session_objs = Session.objects.filter(engagement_info_id=objs.first().id)
            if coachee_obj.num_sessions == session_objs.count():
                all_session_completed = True
            else:
                all_session_completed = False
            response["all_session_completed"] = all_session_completed
            response["total_sessions_allocated"] = coachee_obj.num_sessions
            current_time = timezone.now().time()
            completed_sessions = session_objs.filter(end_time__lt=current_time).count()
            response["total_sessions_completed"] = completed_sessions
            response["total_sessions_remaining"] = (
                    coachee_obj.num_sessions - completed_sessions
            )
            return Response(response)
        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)


class ClientCoacheeSessionReviewViewSet(viewsets.ViewSet):
    """
    This will return the coach and coachee session review detail of a given session id
    """

    permission_classes = [IsClientUser]

    @action(detail=False, methods=["get"])
    def list(self, request, session_id):
        try:
            Session.objects.get(id=session_id, call_type="Coaching Session")
        except:
            return Response({"detail": "invalid session id."})

        try:
            coach_review_obj = CoachReviews.objects.get(session_id=session_id)
            serializer = CoachReviewsSerializer(coach_review_obj)
            coach_review = serializer.data
        except:
            coach_review = {}

        try:
            coachee_review_obj = CoacheesReviews.objects.get(session_id=session_id)
            serializer = CoacheesReviewsSerializer(coachee_review_obj)
            coachee_review = serializer.data
        except:
            coachee_review = {}

        return Response(
            {"coach_review": coach_review, "coachee_review": coachee_review}
        )


class ClientCoacheeFinalReportReviewViewSet(viewsets.ViewSet):
    """
    This will return the coach and coachee fianl report review detail of a given session id
    """

    permission_classes = [IsClientUser]

    @action(detail=False, methods=["get"])
    def list(self, request, engagement_info_id):
        try:
            EngagementInfo.objects.get(
                id=engagement_info_id, is_chemistry_call=True, is_assigned=True
            )
        except:
            return Response({"detail": "invalid engagement info id."})

        try:
            coach_review_obj = CoachFinalReportReview.objects.get(
                engagement_info_id=engagement_info_id
            )
            serializer = FinalReportReviewSerializer(coach_review_obj)
            coach_review = serializer.data
        except:
            coach_review = {}

        try:
            coachee_review_obj = CoacheesFinalReportReview.objects.get(
                engagement_info_id=engagement_info_id
            )
            serializer = FinalReportReviewSerializer(coachee_review_obj)
            coachee_review = serializer.data
        except:
            coachee_review = {}

        return Response(
            {"coach_review": coach_review, "coachee_review": coachee_review}
        )


class ClientAnalyticsAggregateDataAnalytics(viewsets.ViewSet):
    """
    This will return the total session of all coachees of a client and total completed and remaining sessions
    """

    permission_classes = [IsClientUser]

    @action(detail=False, methods=["get"])
    def list(self, request):
        user = request.user.client

        total_sessions_of_all_employees = (
                Coachee.objects.filter(client=user).aggregate(
                    total_sessions=Sum("num_sessions")
                )["total_sessions"]
                or 0
        )
        current_time = timezone.localtime().time()
        total_sessions_completed = Session.objects.filter(
            engagement_info__coachee__client=user,
            call_type="Coaching Session",
            session_date__lte=timezone.now().date(),
            end_time__lt=current_time,
        ).count()
        total_sessions_remaining = (
                total_sessions_of_all_employees - total_sessions_completed
        )

        return Response(
            {
                "total_sessions_allotted_for_all_employees": total_sessions_of_all_employees,
                "total_sessions_completed": total_sessions_completed,
                "total_sessions_remaining": total_sessions_remaining,
            }
        )


class ClientAverageRating(viewsets.ViewSet):
    """
    This will return the all coachees of a cocah whose id is given and average of rating of reviews
    """

    permission_classes = [IsClientUser]
    serializer_class = CoacheeSerializer

    @action(detail=False, methods=["get"])
    def list(self, request, coach_id):
        client = request.user.client
        try:
            coach_instance = Coach.objects.get(id=coach_id)
        except:
            return Response({"detail": "invalid coach id."})

        # Getting all cocahees of a particular coach whose id is given

        coachees_for_coach = Coachee.objects.filter(
            engagement_infos__coach=coach_instance, client=client, num_sessions__gt=0
        ).distinct()
        serializer = self.serializer_class(coachees_for_coach, many=True)

        engagement_infos_objects = EngagementInfo.objects.filter(
            coachee__in=coachees_for_coach, coach=coach_instance
        )

        # finding averge of coach final report average
        coach_final_report_object = CoachFinalReportReview.objects.filter(
            engagement_info__in=engagement_infos_objects
        )
        coach_avg = coach_final_report_object.aggregate(
            avg_rate_1=Avg("rate_1"),
            avg_rate_2=Avg("rate_2"),
            avg_rate_3=Avg("rate_3"),
            avg_rate_4=Avg("rate_4"),
        )

        # finding averge of coachee final report average
        coachee_final_report_object = CoacheesFinalReportReview.objects.filter(
            engagement_info__in=engagement_infos_objects
        )
        coachee_avg = coachee_final_report_object.aggregate(
            avg_rate_1=Avg("rate_1"),
            avg_rate_2=Avg("rate_2"),
            avg_rate_3=Avg("rate_3"),
            avg_rate_4=Avg("rate_4"),
        )
        response = {
            "coachees": serializer.data,
            "coachee_average_rating": {
                "rate_1": coachee_avg["avg_rate_1"],
                "rate_2": coachee_avg["avg_rate_2"],
                "rate_3": coachee_avg["avg_rate_3"],
                "rate_4": coachee_avg["avg_rate_4"],
            },
            "coach_average_rating": {
                "rate_1": coach_avg["avg_rate_1"],
                "rate_2": coach_avg["avg_rate_2"],
                "rate_3": coach_avg["avg_rate_3"],
                "rate_4": coach_avg["avg_rate_4"],
            },
        }
        return Response(response)


def find_or_create_room(room_name, session_obj):
    try:
        twilio_client = twilio.rest.Client(settings.TWILIO_API_SID, settings.TWILIO_API_SECRET,
                                           settings.TWILIO_API_SECRET, )
        # try to fetch an in-progress room with this name
        twilio_client.video.rooms(room_name).fetch()
    except twilio.base.exceptions.TwilioRestException:
        # the room did not exist, so create it
        room = twilio_client.video.rooms.create(unique_name=room_name, type="go")
        SessionCall(
            session=session_obj,
            room_sid=room.sid,
            room_name=room.unique_name,
        ).save()


def get_access_token(room_name):
    # create the access token
    access_token = twilio.jwt.access_token.AccessToken(
        settings.TWILIO_SID,
        settings.TWILIO_API_SID,
        settings.TWILIO_API_SECRET,
        identity=uuid.uuid4().int
    )
    # create the video grant
    video_grant = twilio.jwt.access_token.grants.VideoGrant(room=room_name)
    # Add the video grant to the access token
    access_token.add_grant(video_grant)
    return access_token.to_jwt()


class SessionCallAccessTokenViewSet(viewsets.ViewSet):
    """
    Here we generate access token room sid
    """

    permission_classes = [IsCoachOrCoacheeUser]

    @action(detail=False, methods=["post"])
    def token(self, request, session_id):
        try:

            session_obj = Session.objects.filter(id=session_id)
            if not session_obj.exists():
                return Response(
                    {"detail": "Invalid session id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            find_or_create_room(str(session_id), session_obj.first())
            access_token = get_access_token(str(session_id))

            if isinstance(access_token, bytes):
                access_token = access_token.decode('utf-8')

            # Return the access token as JSON in the response
            return JsonResponse({"token": str(access_token)})
        except Exception as e:
            return JsonResponse({"detail": f"Something went wrong"})