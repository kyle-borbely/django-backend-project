from django.db import models
from django.db.models.signals import post_delete
from users.models import User
from django.dispatch import receiver
import boto3
from django.conf import settings
from django.core.files.storage import default_storage
from home.storage_backends import generate_presigned_url


class Certificate(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        # Remove the relationship with coaches
        self.coach_set.clear()
        # Remove the relationship with the other table
        super(Certificate, self).delete(*args, **kwargs)


class Coach(models.Model):
    class Meta:
        verbose_name = "List of all coach"
        verbose_name_plural = "List of all coaches"

    first_name = models.CharField(max_length=100, blank=False, null=False)
    last_name = models.CharField(max_length=100, blank=False, null=False)
    email = models.EmailField(max_length=50, blank=False, null=False)
    years_of_experience = models.IntegerField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="coach_profile_pictures/", blank=True, null=True
    )
    intro_video = models.FileField(
        upload_to="coach_intro_videos/", blank=True, null=True
    )
    certificates = models.ManyToManyField(Certificate)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=False, blank=False, related_name="coach"
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_profile_picture_url(self, expiration=3600):
        return generate_presigned_url(self.profile_picture.name, expiration)

    def get_intro_video_url(self, expiration=3600):
        return generate_presigned_url(self.intro_video.name, expiration)

    # TODO: Need fix, certificate relational table delete the record but not deleting the name of certificate from coaches_certificate table
    def delete(self, *args, **kwargs):
        # Delete the related certificate names
        self.certificates.set([])
        # Delete the Coach object
        # Delete the associated profile picture and video
        if self.profile_picture:
            default_storage.delete(self.profile_picture.name)
        if self.intro_video:
            default_storage.delete(self.intro_video.name)
        super(Coach, self).delete(*args, **kwargs)

    def delete_intro_video(self):
        """
        Delete the intro video file associated with the coach.
        """
        if self.intro_video:
            default_storage.delete(self.intro_video.name)
            # Delete the file from S3
            s3 = boto3.client("s3")
            s3.delete_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=self.intro_video.name
            )
            # Clear the intro video field and save the object
            self.intro_video = None
            self.save()


@receiver(post_delete, sender=Coach)
def delete_related_user(sender, instance, **kwargs):
    """
    A signal receiver which deletes the corresponding User object when a Coach object is deleted.
    """
    instance.user.delete()


class CoachAvailability(models.Model):
    coach = models.ForeignKey(
        Coach, on_delete=models.CASCADE, related_name="coachavailability"
    )
    date = models.DateField(null=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_reserved = models.BooleanField(default=False)
    utc_offset = models.DurationField(null=True, blank=True)
