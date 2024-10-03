from django.urls import path, include
from rest_framework.routers import DefaultRouter
from home.api.v1.viewsets import (
    SignupViewSet,
    LoginViewSet,
    ClientViewSet,
    CoacheeViewSet,
    CoachViewSet,
    FeedbackViewSet,
    CoachAvailabilityViewSet,
    SessionViewSet,
    CoachAvailabilityListViewSet,
    CoachReviewsViewSet,
    CoacheeReviewsViewSet,
    DeviceRegistration,
    CoachFinalReportViewSet,
    CoacheeFinalReportViewSet,
    NotificationHistoryViewSet,
    SingleNotificationReaderViewSet,
    AllNotificationsReaderViewSet,
    SessionDetailViewSet,
    ClientCoachesViewSet,
    ClientCoacheeSessionsViewSet,
    ClientCoacheeEngagementDetailViewSet,
    ClientCoacheeSessionReviewViewSet,
    ClientCoacheeFinalReportReviewViewSet,
    ClientAnalyticsAggregateDataAnalytics,
    ClientAverageRating,
    SessionCallAccessTokenViewSet,
    CalendlyViewSet
)

router = DefaultRouter()
# router.register("signup", SignupViewSet, basename="signup")
# router.register("login", LoginViewSet, basename="login")
router.register(r"clients", ClientViewSet, basename="clients")
router.register(r"coachees", CoacheeViewSet, basename="coachees")
router.register(r"coaches", CoachViewSet, basename="coaches")
router.register(r"feedbacks", FeedbackViewSet, basename="feedbacks")
router.register(r"coaching_slots", CoachAvailabilityViewSet, basename="coaching_slots")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "coaches/session/students/",
        CoachViewSet.as_view({"get": "coach_students"}),
        name="coach_students",
    ),
    path(
        "coaches/session/<int:coachee_id>/",
        CoachViewSet.as_view({"get": "coach_sessions"}),
        name="coach_sessions",
    ),
    path(
        "coachees/session/<int:coach_id>/",
        CoacheeViewSet.as_view({"get": "coachee_sessions"}),
        name="coachee_sessions",
    ),
    path(
        "coachees/session_or_chemistry_call/<int:engagement_info_id>/",
        SessionViewSet.as_view({"post": "create"}),
        name="session_or_chemistry_call",
    ),
    path(
        "coachees/select_coach/<int:engagement_info_id>/",
        SessionViewSet.as_view({"get": "retrieve"}),
        name="select_coach",
    ),
    path(
        "coaching_slots/<str:coach_id>/calendar/",
        CoachAvailabilityViewSet.as_view({"get": "retrieve"}),
        name="coachavailability-detail",
    ),
    path(
        "coaching_slots_bulk_create_or_update/",
        CoachAvailabilityListViewSet.as_view({"post": "bulk_create_or_update"}),
        name="coachavailability-bulk-create-update",
    ),
    path(
        "coach/review/<int:session_id>/",
        CoachReviewsViewSet.as_view({"post": "create", "get": "retrieve"}),
        name="coach_review",
    ),
    path(
        "coachees/review/<int:session_id>/",
        CoacheeReviewsViewSet.as_view({"post": "create", "get": "retrieve"}),
        name="coachees_review",
    ),
    path(
        "store_fcm_token/<device_token>/",
        DeviceRegistration.as_view({"post": "create"}),
        name="device_registration",
    ),
    path(
        "coach/final_report_review/<int:engagement_id>/",
        CoachFinalReportViewSet.as_view({"post": "create", "get": "retrieve"}),
        name="coach_final_report_review",
    ),
    path(
        "coachee/final_report_review/<int:engagement_id>/",
        CoacheeFinalReportViewSet.as_view({"post": "create", "get": "retrieve"}),
        name="coachee_final_report_review",
    ),
    path(
        "notifications/history/",
        NotificationHistoryViewSet.as_view({"get": "list"}),
        name="notification-history",
    ),
    path(
        "notifications/read/<notification_id>/",
        SingleNotificationReaderViewSet.as_view({"patch": "partial_update"}),
        name="single_notification_reader",
    ),
    path(
        "notifications/read/",
        AllNotificationsReaderViewSet.as_view({"patch": "partial_update"}),
        name="all_notifications_reader",
    ),
    path(
        "sessions/<session_id>/",
        SessionDetailViewSet.as_view({"get": "retrieve"}),
        name="session_detail",
    ),
    path(
        "clients/employees/sessions/<int:engagement_info_id>/",
        ClientCoacheeSessionsViewSet.as_view({"get": "list"}),
        name="client_employee_sessions",
    ),
    path(
        "clients/employees/engagement_info/<int:coachee_id>/",
        ClientCoacheeEngagementDetailViewSet.as_view({"get": "list"}),
        name="client_coachee_detail",
    ),
    path(
        "clients/coaches",
        ClientCoachesViewSet.as_view({"get": "list"}),
        name="client_coachees",
    ),
    path(
        "clients/employees/session/reviews/<int:session_id>/",
        ClientCoacheeSessionReviewViewSet.as_view({"get": "list"}),
        name="session_reviews_detail",
    ),
    path(
        "clients/employees/final_report/reviews/<int:engagement_info_id>/",
        ClientCoacheeFinalReportReviewViewSet.as_view({"get": "list"}),
        name="final_report_review_detail",
    ),
    path(
        "clients/analytics/aggregate_data/",
        ClientAnalyticsAggregateDataAnalytics.as_view({"get": "list"}),
        name="client_aggregate_data_analytics",
    ),
    path(
        "clinets/analytics/average_rating/<int:coach_id>/",
        ClientAverageRating.as_view({"get": "list"}),
        name="sessions_average",
    ),
    path(
        "session_call/create_room/<int:session_id>",
        SessionCallAccessTokenViewSet.as_view({"post": "token"}),
        name="access_token",
    ),
    path(
        "calendly_calender/<int:coach_id>",
        CalendlyViewSet.as_view({"get": "list"}),
        name="calendly_calnder"
    ),
    path(
        "calendly_calender/deactivate",
        CalendlyViewSet.as_view({"post": "deactivate"}),
        name="calendly_calnder"
    )
]
