from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "users"
    verbose_name = _("Admin Panel Users")

    def ready(self):
        try:
            import users.signals  # noqa F401
        except ImportError:
            pass
