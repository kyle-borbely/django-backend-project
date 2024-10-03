from rest_auth.views import LoginView


class CustomLoginView(LoginView):
    def get_response(self):
        response = super().get_response()

        # Get the user object
        user = self.user
        if user is not None:
            user_type_id = None
            if user.user_type == "Client":
                user_type_id = user.client.id
            elif user.user_type == "Coach":
                user_type_id = user.coach.id
            elif user.user_type == "Coachee":
                user_type_id = user.coachee.id

            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user.user_type,
                "user_type_id": user_type_id,
                "is_new_user": user.is_new_user,
            }
            response.data["user"] = user_data

            # Update the is_new_user field to False
            user.is_new_user = False
            user.save()

        return response
