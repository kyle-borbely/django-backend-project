from django.urls import path
from coaches.views import (
    coach_redirect_view,
    coach_update_view,
    coach_detail_view,
    coach_add_view,
)

app_name = "coaches"
urlpatterns = [
    path("~redirect/", view=coach_redirect_view, name="redirect"),
    path("~update/", view=coach_update_view, name="update"),
    path("<str:username>/", view=coach_detail_view, name="detail"),
    path("add/", view=coach_add_view, name="coache_add"),
]
