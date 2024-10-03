"""
    In this project we use django-apscheduler==0.6.0 module for notifications which will sent at 8 AM 
    And we use django-background-tasks4 == 1.3.0 module to schedule session notifications 
    we use seprate modules because in APSchedule when we scedule session notifications sometimes it will not execute 
    and in django-background-task4 we are facing some a issues to schedule notification for 8am 
"""


from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.triggers.cron import CronTrigger
from notifications.models import Notification, NotificationHistory
from users.models import User
from django.db.models import Q
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification as FCM_Notification
from django.db import connection
from coaches.models import Coach
from coachees.models import Session
from background_task import background


def send_notification(receivers, noti_name, noti_text, action_type):
    """
    This Function will send the notifications(which is sent by admin pannel) to all the receivers which will passed as an argument
    """
    try:
        for user in receivers:
            devices = FCMDevice.objects.filter(user=user)
            if devices.exists():
                for device in devices:
                    response = device.send_message(
                        Message(
                            notification=FCM_Notification(
                                title=noti_name,
                                body=noti_text,
                            ),
                            data={"action_type": action_type},
                        )
                    )
    except:
        pass
        NotificationHistory.objects.create(
            user=user,
            notification_name=noti_name,
            notification_text=noti_text,
            action_type=action_type,
        )


def Notification_at_8():
    """
    This function filters all the notifications scheduled to send daily at 8 AM
    and sends them to their related receivers.
    """
    periodic_notifications = Notification.objects.filter(activate="every_day_at_8")
    if periodic_notifications.exists():
        for noti in periodic_notifications:
            receiver = noti.receiver
            if receiver == "All":
                users = User.objects.filter(
                    Q(user_type="Coach") | Q(user_type="Coachee")
                )
            else:
                users = User.objects.filter(user_type=receiver)
            send_notification(
                receivers=users,
                noti_name=noti.notification_name,
                noti_text=noti.notification_text,
                action_type="every_day_at_8_am",
            )


@background
def schedule_session_notifications(kwargs):
    """
    This function will send notification to the coach to review the coachee
    """
    try:
        coach_id = kwargs.get("coach_id")
        coach_obj = Coach.objects.filter(id=coach_id).first()
        user_obj = User.objects.get(id=coach_obj.user_id)
        devices = FCMDevice.objects.filter(user=user_obj)
        if devices.exists():
            for device in devices:
                device.send_message(
                    Message(
                        notification=FCM_Notification(
                            title=kwargs.get("notification_name"),
                            body=kwargs.get("notification_text"),
                            image=kwargs.get("profile_picture"),
                        ),
                        data={
                            "action_type": str(kwargs.get("action_type")),
                            "coach_id": str(kwargs.get("coach_id")),
                            "coachee_id": str(kwargs.get("coachee_id")),
                            "engagement_info_id": str(kwargs.get("engagement_info_id")),
                            "session_id": str(kwargs.get("session_id")),
                        },
                    )
                )
    except:
        pass
    NotificationHistory.objects.create(
        user=user_obj,
        notification_name=kwargs.get("notification_name"),
        notification_text=kwargs.get("notification_text"),
        action_type=kwargs.get("action_type"),
        data={
            "coach_id": kwargs.get("coach_id"),
            "coachee_id": kwargs.get("coachee_id"),
            "engagement_info_id": kwargs.get("engagement_info_id"),
            "session_id": kwargs.get("session_id"),
            "profile_picture": None,
        },
    )

    session_id = kwargs.get("session_id")
    session_obj = Session.objects.filter(id=session_id)
    if session_obj.exists():
        so = session_obj.first()
        so.is_notify = True
        so.save()

    return


def notifications(
    action_type,
    user_id,
    notification_name,
    notification_text,
    fcm_data,
    history_data={},
    profile_picture="",
):
    try:
        user_obj = User.objects.get(id=user_id)
        devices = FCMDevice.objects.filter(user=user_obj)
        if devices.exists():
            for device in devices:
                device.send_message(
                    Message(
                        notification=FCM_Notification(
                            title=notification_name,
                            body=notification_text,
                            image=profile_picture,
                        ),
                        data=fcm_data,
                    )
                )
    except:
        pass

    NotificationHistory.objects.create(
        user=user_obj,
        notification_name=notification_name,
        notification_text=notification_text,
        action_type=action_type,
        data=history_data,
    )


# creating an object of BacgroundScheduler which is responsible for all jobs
session_ending_notification_schedule = BackgroundScheduler()
# Adding default jobstore
session_ending_notification_schedule.add_jobstore(DjangoJobStore(), "default")

# Adding job to call function daily at 8AM
session_ending_notification_schedule.add_job(
    Notification_at_8,
    trigger=CronTrigger(hour=8, minute=0),
    id="Daily 8AM Notifications",
    replace_existing=True,
)

# # Here we start our scheduler
# if not session_ending_notification_schedule.running:
#     session_ending_notification_schedule.start()

# Check if the required table exists before starting the scheduler
if "django_apscheduler_djangojob" in connection.introspection.table_names():
    if not session_ending_notification_schedule.running:
        session_ending_notification_schedule.start()
else:
    print("Required database table 'django_apscheduler_djangojob' does not exist.")
