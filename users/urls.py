from django.urls import path
from users.views import (
    user_redirect_view,
    user_update_view,
    user_detail_view,
    user_create_view,
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
    path("add/", view=user_create_view, name="users_add"),
]
