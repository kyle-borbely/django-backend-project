from django.urls import path
from coachees.views import AssignCoachView, session_report, final_report

app_name = "coachees"
urlpatterns = [
    path(
        "coachees/assign_coach/<int:pk>/",
        view=AssignCoachView.as_view(),
        name="assign_coach",
    ),
    path("<int:pk>/assign-coach/", view=AssignCoachView.as_view(), name="assign_coach"),
    path("session-report/<session_id>/", session_report, name="session-report"),
    path("final-report/<engagement_id>/", final_report, name="final-report"),
]
