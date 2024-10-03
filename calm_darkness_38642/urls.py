"""calm_darkness_38642 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic.base import TemplateView
from drf_spectacular.views import SpectacularJSONAPIView, SpectacularSwaggerView
from .views import CustomLoginView
from home.views import (
    PasswordResetView,
    PasswordResetConfirmView,
    CustomPasswordResetConfirmView,
    CustomPasswordChangeView,
    MobilePasswordResetView,
    VerifyOTPView,
)

urlpatterns = [
    path("accounts/", include("allauth.urls")),
    path("modules/", include("modules.urls")),
    path("api/v1/", include("home.api.v1.urls")),
    path("admin/", admin.site.urls),
    path("users/", include("users.urls", namespace="users")),
    path("clients/", include("clients.urls", namespace="clients")),
    path("coachees/", include("coachees.urls", namespace="coachees")),
    path("feedbacks/", include("feedbacks.urls", namespace="feedbacks")),
    # Override custom rest_auth apis, these must be above on "path("rest-auth/", include("rest_auth.urls"))"
    path("rest-auth/login/", CustomLoginView.as_view(), name="rest_login"),
    path(
        "rest-auth/password/change/",
        CustomPasswordChangeView.as_view(),
        name="rest_password_change",
    ),
    path(
        "rest-auth/password/reset/",
        PasswordResetView.as_view(),
        name="rest_password_reset",
    ),
    path(
        "rest-auth/password/reset/otp/",
        MobilePasswordResetView.as_view(),
        name="otp_password_reset",
    ),
    path("rest-auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path(
        "new-password/<str:uidb64>/<str:token>/",
        CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("rest-auth/", include("rest_auth.urls")),
]


admin.site.site_header = "Sloan Leaders"
admin.site.site_title = "Sloan Leaders Admin Portal"
admin.site.index_title = "Sloan Leaders Admin"

# swagger
urlpatterns += [
    path("api-docs/schema/", SpectacularJSONAPIView.as_view(), name="schema"),
    path(
        "api-docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api_docs"
    ),
]

urlpatterns += [re_path(r".*", TemplateView.as_view(template_name="index.html"))]
