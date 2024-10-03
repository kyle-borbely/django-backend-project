from rest_framework.permissions import IsAuthenticated


class IsClientUser(IsAuthenticated):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and request.user.user_type == "Client"
        )


class IsCoacheeUser(IsAuthenticated):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.user_type == "Coachee"
        )


class IsCoachUser(IsAuthenticated):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and request.user.user_type == "Coach"
        )


class IsClientOrCoacheeUser(IsAuthenticated):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == "Client" or request.user.user_type == "Coachee"
        )


class IsCoachOrCoacheeUser(IsAuthenticated):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == "Coach" or request.user.user_type == "Coachee"
        )


class IsCoachCoacheeOrClientUser(IsAuthenticated):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == "Coach"
            or request.user.user_type == "Coachee"
            or request.user.user_type == "Client"
        )
