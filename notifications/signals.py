from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from datetime import datetime
from coachees.models import (
    CoachReviews,
    Session,
    EngagementInfo,
    CoachFinalReportReview,
    Coachee,
)
from users.models import User
from fcm_django.models import FCMDevice
from datetime import datetime
from firebase_admin.messaging import Message, Notification as FCM_Notification
from .models import NotificationHistory
from clients.models import Client
from calm_darkness_38642.schedular import notifications

# from django.conf import settings
# import pytz
# from datetime import datetime, timedelta

# TODO should remove after sprint 3 when notification worked properly. today date (Sep, 13, 2023)

# @receiver(post_save, sender=Session)
# def notifications_for_session(sender, instance, created, **kwargs):
#     """
#     When a new Session is created it will execute and add job to send notification on the ending time of the session
#     to review the coachee
#     """
#     if created and (instance.call_type == "Coaching Session"):
#         session_date = instance.session_date
#         end_time = instance.end_time
#         utc_offset_str = instance.utc_offset
#
#         session_date_obj = datetime.strptime(str(session_date), "%Y-%m-%d")
#         session_end_time_obj = datetime.strptime(str(end_time), "%H:%M:%S")
#         utc_offset = instance.utc_offset
#         settings_timezone = pytz.timezone(settings.TIME_ZONE)
#         # combining the session date and session ending time
#         session_datetime_obj = datetime.combine(
#             session_date_obj.date(), session_end_time_obj.time()
#         )
#         schedular_session_date = session_datetime_obj.strftime("%Y-%m-%d %H:%M:%S") + utc_offset_str
#
#         print(f'session_datetime_obj: {session_datetime_obj}')
#         print(f'session_datetime_obj_with_offset --- formatted_datetime: {schedular_session_date}')
#         print(type(schedular_session_date))
#         # ###
#         # offset_hours = int(utc_offset[:3])
#         # offset_minutes = int(utc_offset[4:6])
#         #
#         # # Create a timedelta with the UTC offset
#         # utc_offset_timedelta = timedelta(hours=offset_hours, minutes=offset_minutes)
#         #
#         # # Apply the UTC offset to the combined datetime
#         # session_datetime_obj_with_offset = session_datetime_obj + utc_offset_timedelta
#         #
#         # # Convert to the settings timezone
#         # session_datetime_obj_with_offset_in_settings_timezone = session_datetime_obj_with_offset.astimezone(
#         #     settings_timezone).replace(tzinfo=pytz.UTC)
#         #
#         # print('here wit timezone in americe ....')
#         # print(session_datetime_obj_with_offset_in_settings_timezone)
#         ####
#         coach = instance.engagement_info.coach
#         coachee = instance.engagement_info.coachee
#
#         # kwargs to pass in the function which send notification to coach
#         kwargs = {
#             "action_type": "coachee_review",
#             "detail": {
#                 "coachee_id": coachee.user_id,
#                 "profile_picture": coachee.profile_picture.url
#                 if coachee.profile_picture
#                 else None,
#                 "notification_name": "Please review the coachee",
#                 "notification_text": coachee.first_name
#                 + " "
#                 + coachee.last_name
#                 + " review",
#             },
#             "coach_id": coach.user_id,
#             "engagement_info_id": instance.engagement_info.id,
#             "session_id": instance.id,
#         }
#         from calm_darkness_38642.schedular import (
#             session_ending_notification_schedule,
#             session_notifications,
#         )
#         # Scheduling
#         job = session_ending_notification_schedule.add_job(
#             session_notifications,
#             trigger="date",
#             run_date= schedular_session_date, #'2023-09-13 16:39:00+05:00',
#             kwargs=kwargs,
#             id=f"Session id is {instance.id}",
#             jobstore="default",
#         )


@receiver(post_save, sender=CoachReviews)
def notification_for_coachees_and_coach_final_report(
    sender, instance, created, **kwargs
):
    """
    When the Coach sumbit review of the coachee then this recevier will execute and send notification
    to review the coach and this fucntion also send notification to client
    """
    session_id = instance.session_id
    session_obj = Session.objects.get(id=session_id)
    coachee = session_obj.engagement_info.coachee
    coach = session_obj.engagement_info.coach
    user_id = coachee.user_id
    user_obj = User.objects.get(id=user_id)
    devices = FCMDevice.objects.filter(user=user_obj)
    detail = kwargs.get("detail")

    engagement_id = session_obj.engagement_info_id
    engagement_obj = EngagementInfo.objects.get(id=engagement_id)
    session_objects = Session.objects.filter(
        engagement_info_id=engagement_id, call_type="Coaching Session"
    )
    if coachee.num_sessions == session_objects.count():
        for obj in session_objects:
            # if the review of any session is not submitted then we break the loop and notification will not send
            review_obj = CoachReviews.objects.filter(session_id=obj.id)
            if not review_obj.exists():
                break
        else:
            coach_user_id = coach.user_id
            coach_user_object = User.objects.get(id=coach_user_id)
            coach_devices = FCMDevice.objects.filter(user=coach_user_object)
            try:
                if coach_devices.exists():
                    for device in coach_devices:
                        response = device.send_message(
                            Message(
                                notification=FCM_Notification(
                                    title=f"All Coaching Sessions with {coachee.first_name} {coachee.last_name} have been completed. Please share your feedback in a Final Report here.",
                                    body=coachee.first_name
                                    + " "
                                    + coachee.last_name
                                    + " review",
                                    image=str(coachee.profile_picture.url)
                                    if coachee.profile_picture
                                    else "",
                                ),
                                data={
                                    "action_type": "coachee_final_report_review",
                                    "coach_id": str(coach.id),
                                    "coachee_id": str(coachee.id),
                                    "engagement_info_id": str(engagement_id),
                                },
                            ),
                        )
            except:
                pass
            NotificationHistory.objects.create(
                user=coach_user_object,
                notification_name=f"All Coaching Sessions with {coachee.first_name} {coachee.last_name} have been completed. Please share your feedback in a Final Report here.",
                notification_text=coachee.first_name
                + " "
                + coachee.last_name
                + " review",
                action_type="coachee_final_report_review",
                data={
                    "coach_id": coach.id,
                    "engagement_info_id": engagement_id,
                    "coachee_id": coachee.id,
                    "profile_picture": None,
                },
            )

    # sending notification to coachee for session review
    try:
        if devices.exists():
            for device in devices:
                response = device.send_message(
                    Message(
                        notification=FCM_Notification(
                            title="Please provide feedback from your Coaching Session.",
                            body=coach.first_name + " " + coach.last_name + " review",
                            image=str(coach.profile_picture.url)
                            if coach.profile_picture
                            else "",
                        ),
                        data={
                            "action_type": "coach_review",
                            "coachee_id": str(coachee.id),
                            "coach_id": str(coach.id),
                            "engagement_info_id": str(engagement_id),
                            "session_id": str(session_id),
                        },
                    )
                )
    except:
        pass
    # here we store the the data of notification
    NotificationHistory.objects.create(
        user=user_obj,
        notification_name="Please provide feedback from your Coaching Session.",
        notification_text=coach.first_name + " " + coach.last_name + " review",
        action_type="coach_review",
        data={
            "coach_id": coach.id,
            "coachee_id": coachee.id,
            "engagement_info_id": engagement_id,
            "session_id": session_id,
            "profile_picture": None,
        },
    )
    # is_notify flag is only for frontend
    session_object = Session.objects.filter(id=session_id)
    if session_object.exists():
        so = session_object.first()
        so.is_notify = False
        so.is_reviewed_by_coach = True
        so.save()

    # Sending Notification to client

    action_type = "coach_review_for_client"
    client_user_id = coachee.client.user_id
    notification_name = f"{coachee.first_name} {coachee.last_name} received a review from their Coaching Session."
    notification_text = ""
    profile_picture = (
        str(session_obj.engagement_info.coachee.profile_picture.url)
        if session_obj.engagement_info.coachee.profile_picture
        else "",
    )
    fcm_data = {
        "action_type": action_type,
        "coach_id": coach.id,
        "coachee_id": coachee.id,
        "engagement_info_id": engagement_id,
        "session_id": session_id,
    }
    history_data = {
        "coach_id": coach.id,
        "coachee_id": coachee.id,
        "engagement_info_id": engagement_id,
        "session_id": session_id,
        "profile_picture": None,
    }

    notifications(
        action_type=action_type,
        user_id=client_user_id,
        notification_name=notification_name,
        notification_text=notification_text,
        fcm_data=fcm_data,
        history_data=history_data,
        profile_picture=profile_picture,
    )

    return


def final_report_notification_for_coachee(sender, instance, created, **kwargs):
    """
    This fucntion will send final report review notification to coachee and it also notify the client
    """
    if created:
        engagement_id = instance.engagement_info_id
        current_date = datetime.now().date()

        # updating the end date of engagement
        engagement_obj = EngagementInfo.objects.get(id=engagement_id)
        engagement_obj.end_date = current_date
        engagement_obj.save()

        coachee_user_id = instance.engagement_info.coachee.user_id

        # updating engagement status
        coachee_obj = Coachee.objects.get(user_id=coachee_user_id)
        coachee_obj.engagement_status = "End Engagement"
        coachee_obj.save()

        # sending notification to coachee for final report
        user_obj = User.objects.get(id=coachee_user_id)
        devices = FCMDevice.objects.filter(user=user_obj)
        coach = instance.engagement_info.coach
        try:
            if devices.exists():
                for device in devices:
                    response = device.send_message(
                        Message(
                            notification=FCM_Notification(
                                title="You have completed all of your assigned Coaching Sessions. Please share your experience in a Final Report here.",
                                body=coach.first_name
                                + " "
                                + coach.last_name
                                + " review",
                                image=str(coach.profile_picture.url)
                                if coach.profile_picture
                                else "",
                            ),
                            data={
                                "action_type": "coach_final_report_review",
                                "coachee_id": str(engagement_obj.coachee.id),
                                "coach_id": str(engagement_obj.coach.id),
                                "engagement_info_id": str(engagement_id),
                            },
                        ),
                    )
        except:
            pass
        NotificationHistory.objects.create(
            user=user_obj,
            notification_name="You have completed all of your assigned Coaching Sessions. Please share your experience in a Final Report here.",
            notification_text=coach.first_name + " " + coach.last_name + " review",
            action_type="coach_final_report_review",
            data={
                "coach_id": coach.id,
                "coachee_id": coachee_obj.id,
                "engagement_info_id": engagement_id,
                "profile_picture": None,
            },
        )

        # Sending Notification to client for coach final report submission
        action_type = "coach_final_report_review_for_client"
        client_user_id = instance.engagement_info.coachee.client.user_id
        notification_name = f"{coachee_obj.first_name} {coachee_obj.last_name} received a Final Report from their Executive Coach."
        notification_text = ""
        profile_picture = (
            str(instance.engagement_info.coachee.profile_picture.url)
            if instance.engagement_info.coachee.profile_picture
            else "",
        )
        coach = instance.engagement_info.coach
        coachee = instance.engagement_info.coachee
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
            user_id=client_user_id,
            notification_name=notification_name,
            notification_text=notification_text,
            fcm_data=fcm_data,
            history_data=history_data,
            profile_picture=profile_picture,
        )


post_save.connect(final_report_notification_for_coachee, sender=CoachFinalReportReview)
