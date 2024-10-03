from django.db import models
from users.models import User
from clients.models import Client
from coaches.models import Coach

from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
from home.storage_backends import generate_presigned_url


class Coachee(models.Model):
    class Meta:
        verbose_name = "List of all coachee"
        verbose_name_plural = "List of all coachees"

    first_name = models.CharField(max_length=100, blank=False, null=False)
    last_name = models.CharField(max_length=100, blank=False, null=False)
    email = models.EmailField(max_length=50, blank=False, null=False)
    title = models.CharField(max_length=100, blank=False, null=False)
    department = models.CharField(max_length=100, blank=True, null=True)
    num_sessions = models.IntegerField(default=0)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="coachees",
    )

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Start Engagement", "Start Engagement"),
        ("End Engagement", "End Engagement"),
    )

    engagement_status = models.CharField(
        choices=STATUS_CHOICES, default="Pending", max_length=30
    )
    STATUS = (
        ("Assigned", "Assigned"),
        ("Not Assigned", "Not Assigned"),
    )
    coaching_status = models.CharField(
        choices=STATUS, default="Not Assigned", max_length=30
    )

    city = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    contact_number = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="coachee_profile_pictures/", blank=True, null=True
    )
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=False, blank=False, related_name="coachee"
    )

    def __str__(self):
        return self.first_name + " " + self.last_name

    def get_profile_picture_url(self, expiration=3600):
        return generate_presigned_url(self.profile_picture.name, expiration)

    def delete(self, *args, **kwargs):
        # Delete the associated profile picture and video
        if self.profile_picture:
            default_storage.delete(self.profile_picture.name)
        super(Coachee, self).delete(*args, **kwargs)


@receiver(post_delete, sender=Coachee)
def delete_related_user(sender, instance, **kwargs):
    """
    A signal receiver which deletes the corresponding User object when a Coachee object is deleted.
    """
    instance.user.delete()


class EngagementInfo(models.Model):
    class Meta:
        verbose_name = "EngagementInfo"

    coachee = models.ForeignKey(
        Coachee, on_delete=models.CASCADE, related_name="engagement_infos"
    )
    coach = models.ForeignKey(
        Coach, on_delete=models.CASCADE, related_name="engagement_infos"
    )

    is_chemistry_call = models.BooleanField(default=False)
    is_assigned = models.BooleanField(default=False)
    num_scheduled_sessions = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def _str_(self):
        return f"{self.coachee} - {self.coach}"


class Session(models.Model):
    class Meta:
        verbose_name = "Session"

    engagement_info = models.ForeignKey(
        EngagementInfo, on_delete=models.CASCADE, related_name="sessions"
    )
    session_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    call_type_choices = [
        ("Chemistry Call", "Chemistry Call"),
        ("Coaching Session", "Coaching Session"),
    ]
    call_type = models.CharField(max_length=20, choices=call_type_choices)
    # this flag is for frontend
    is_notify = models.BooleanField(default=False)
    is_reviewed_by_coach = models.BooleanField(default=False)
    is_reviewed_by_coachee = models.BooleanField(default=False)
    utc_offset = models.DurationField(null=True, blank=True)

    def _str_(self):
        return f"{self.engagement_info} - {self.session_date}"


class CoachReviews(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=False)
    CHOICES = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
    rate = models.IntegerField(choices=CHOICES)
    comment = models.TextField(max_length=300, default="", blank=True)

    def clean(self):
        rate = self.rate
        if (rate > 5) or (rate < 0):
            raise ValidationError("Rate's value should be between 1 to 5")


def rate_validation(**kwargs):
    rate_1 = kwargs["rate_1"]
    rate_2 = kwargs["rate_2"]
    rate_3 = kwargs["rate_3"]
    rate_4 = kwargs["rate_4"]
    if (
        (rate_1 > 5)
        or (rate_1 <= 0)
        or (rate_2 > 5)
        or (rate_2 <= 0)
        or (rate_3 > 5)
        or (rate_3 <= 0)
        or (rate_4 > 5)
        or (rate_4 <= 0)
    ):
        return "Rate's value should be between 1 to 5"
    return None


class CoacheesReviews(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=False)
    CHOICES = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
    rate_1 = models.IntegerField(choices=CHOICES)
    comment = models.TextField(max_length=300, default="", blank=True)

    def clean(self):
        rate_1 = self.rate_1
        if (rate_1 > 5) or (rate_1 <= 0):
            raise ValidationError("Rate's value should be between 1 to 5")


class CoacheesFinalReportReview(models.Model):
    engagement_info = models.ForeignKey(
        EngagementInfo,
        on_delete=models.CASCADE,
        related_name="coachee_final_report_review",
    )
    CHOICES = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
    rate_1 = models.IntegerField(choices=CHOICES)
    rate_2 = models.IntegerField(choices=CHOICES)
    rate_3 = models.IntegerField(choices=CHOICES)
    rate_4 = models.IntegerField(choices=CHOICES)
    comment = models.TextField(max_length=300, default="", blank=True)

    def clean(self):
        validation = rate_validation(
            rate_1=self.rate_1,
            rate_2=self.rate_2,
            rate_3=self.rate_3,
            rate_4=self.rate_4,
        )
        if validation is not None:
            raise ValidationError(validation)


class CoachFinalReportReview(models.Model):
    engagement_info = models.ForeignKey(
        EngagementInfo,
        on_delete=models.CASCADE,
        related_name="coach_final_report_review",
    )
    CHOICES = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
    rate_1 = models.IntegerField(choices=CHOICES)
    rate_2 = models.IntegerField(choices=CHOICES)
    rate_3 = models.IntegerField(choices=CHOICES)
    rate_4 = models.IntegerField(choices=CHOICES)
    comment = models.TextField(max_length=300, default="", blank=True)

    def clean(self):
        validation = rate_validation(
            rate_1=self.rate_1,
            rate_2=self.rate_2,
            rate_3=self.rate_3,
            rate_4=self.rate_4,
        )
        if validation is not None:
            raise ValidationError(validation)


class SessionCall(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=False)
    room_sid = models.CharField(max_length=300)
    room_name = models.CharField(max_length=300)
