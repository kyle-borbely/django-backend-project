from django.db import models
import pyotp
from users.models import User
from django.utils import timezone


class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    otp_secret = models.CharField(max_length=32)

    def send_otp(self):
        totp = pyotp.TOTP(self.otp_secret, interval=600)
        otp = totp.now()
        return otp

    def generate_otp_secret(self):
        self.otp_secret = pyotp.random_base32()
        self.created_at = timezone.now()
        self.verified = False
        self.save()

    def verify_otp(self, otp):
        totp = pyotp.TOTP(self.otp_secret, interval=600)
        return totp.verify(otp)

    def __str__(self):
        return self.email
