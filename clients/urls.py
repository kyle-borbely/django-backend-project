from django.urls import path

from clients.views import (
    client_redirect_view,
    client_update_view,
    client_detail_view,
    client_add_view
)

app_name = "clients"
urlpatterns = [
    path("~redirect/", view=client_redirect_view, name="redirect"),
    path("~update/", view=client_update_view, name="update"),
    path("<str:username>/", view=client_detail_view, name="detail"),
    path("add/", view=client_add_view, name="clients_add"),
]
