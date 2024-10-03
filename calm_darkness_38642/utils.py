from django.conf import settings
from calm_darkness_38642.settings import env
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, HtmlContent, Email
from django.core.mail import EmailMessage
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from rest_framework import serializers
from datetime import datetime, timedelta
import pytz
import re
from modules.django_calendly.calendly.models import CalendlyToken
import base64
import os
import requests
from django.utils import timezone
import time
MAX_IMAGE_SIZE = 1024  # Specify the maximum size in pixels


def send_email(to_email, subject, html_content):
    sender_email = settings.SENDGRID_SENDER
    api_key = settings.SENDGRID_API_KEY
    from_email = Email(sender_email, "Sloan Leaders")
    # create a Mail object
    mail = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=HtmlContent(html_content),
    )

    try:
        # send the email using SendGrid API
        sg = SendGridAPIClient(api_key)
        response = sg.send(mail)
        return response
    except Exception as e:
        print(str(e))


def send_invitation(recipient, subject, html_content, ics_content):
    email = EmailMessage(
        subject=subject,
        body=html_content,
        to=[recipient],
    )
    email.attach("invitation.ics", ics_content, "text/calendar")
    email.content_subtype = "html"  # Set the content subtype to HTML
    email.send()


class CompressedImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, (InMemoryUploadedFile, TemporaryUploadedFile)):
            file_data = data.read()
            image = Image.open(BytesIO(file_data))
            compressed_image = self.compress_image(image)
            # Create an InMemoryUploadedFile with the compressed image data
            compressed_file = InMemoryUploadedFile(
                BytesIO(compressed_image),
                None,
                data.name,
                data.content_type,
                None,
                None,
            )

            return compressed_file

        return super().to_internal_value(data)

    def compress_image(self, image):
        # Convert RGBA image to RGB mode if needed
        if image.mode == "RGBA":
            image = image.convert("RGB")
        # Resize the image while maintaining the aspect ratio
        image.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.ANTIALIAS)
        # Create a BytesIO object to store the compressed image data
        compressed_image = BytesIO()
        # Preserve the EXIF metadata, including orientation
        if hasattr(image, "_getexif"):
            exif = image.info.get("exif")
            if exif:
                # Save the compressed image to the BytesIO object in JPEG format with quality 70
                image.save(
                    compressed_image,
                    format="JPEG",
                    quality=70,
                    exif=exif,
                    optimize=True,
                    copy_exif=True,
                )
            else:
                image.save(compressed_image, format="JPEG", quality=70, optimize=True)
        else:
            image.save(compressed_image, format="JPEG", quality=70, optimize=True)
        # Move the file pointer to the beginning of the BytesIO object
        compressed_image.seek(0)

        return compressed_image.getvalue()


def get_utc_offset(timezone_name):
    try:
        timezone = pytz.timezone(timezone_name)
        current_time_utc = datetime.utcnow()
        offset = timezone.utcoffset(current_time_utc)
        hours = offset.total_seconds() // 3600
        minutes = (offset.total_seconds() % 3600) // 60
        formatted_offset = (
            f"{'+' if hours >= 0 else '-'}{abs(int(hours)):02}:{abs(int(minutes)):02}"
        )

        return formatted_offset
    except pytz.UnknownTimeZoneError:
        return None


def convert_utc_offset(start_datetime, end_datetime, utc_offset):
    def converter(date_time_obj, utc_offset):
        try:
            # Parse the input UTC offset string to extract hours and minutes
            offset_parts = re.match(r"^([+\-])(\d{2}):(\d{2})$", utc_offset)
            if offset_parts:
                sign, hours, minutes = offset_parts.groups()
                hours = int(hours)
                minutes = int(minutes)
                total_offset_minutes = (
                    (hours * 60 + minutes) if sign == "+" else -(hours * 60 + minutes)
                )
            else:
                raise ValueError("Invalid input UTC offset format")

            settings_utc_offset = get_utc_offset(settings.TIME_ZONE)

            def get_total_minutes_from_utc_offset(utc_offset):
                # Split the UTC offset string into hours and minutes
                sign, time_str = utc_offset[0], utc_offset[1:]
                hours_str, minutes_str = time_str.split(":")

                # Convert the hours and minutes to integers
                hours = int(hours_str)
                minutes = int(minutes_str)

                # Calculate the total minutes for the UTC offset
                total_minutes = hours * 60 + minutes

                # Adjust the sign based on the original sign in the UTC offset
                if sign == "-":
                    total_minutes = -total_minutes

                return total_minutes

            # Calculate the time difference as a timedelta
            target_utc_offset_minutes = get_total_minutes_from_utc_offset(
                settings_utc_offset
            )  # Target UTC offset: -04:00
            time_difference_minutes = total_offset_minutes - target_utc_offset_minutes
            time_difference = timedelta(minutes=time_difference_minutes)

            # Adjust the input datetime by subtracting the time difference
            adjusted_datetime = date_time_obj - time_difference

            return adjusted_datetime

        except ValueError as e:
            return str(e)

    converted_start_datetime = converter(
        date_time_obj=start_datetime, utc_offset=utc_offset
    )
    converted_end_datetime = converter(
        date_time_obj=end_datetime, utc_offset=utc_offset
    )

    date = converted_start_datetime.date()
    return (converted_start_datetime, converted_end_datetime, date)


# # Example usage:
# timezone_name = "America/New_York"
# utc_offset = get_utc_offset(timezone_name)

# if utc_offset is not None:
#     print(f"UTC offset for {timezone_name}: {utc_offset}")
# else:
#     print(f"Timezone '{timezone_name}' not found.")

def calendly_get_header(coach):
    try:
        token_record = CalendlyToken.objects.get(user=coach.user)
        if token_record.expires_at <= timezone.now():
            payload = {
                'grant_type': 'refresh_token',
                'refresh_token': token_record.refresh_token,
            }

            token = env.str("CALENDLY_CLIENT_ID") + ':' + env.str("CALENDLY_CLIENT_SECRET")
            byte_token = base64.b64encode(bytes(token, 'utf-8')).decode('utf-8')
            header = {
                'Content-Type': 'application/x-www-form-urlencoded',
                "Authorization": f'Basic {byte_token}',
            }
            response = requests.post(url="https://auth.calendly.com/oauth/token", headers=header,
                                        data=payload)
            response.raise_for_status()
            if response.status_code == 200:
                data = response.json()
                token_record.access_token = data['access_token']
                token_record.refresh_token = data['refresh_token']
                token_record.expires_at = timezone.now() + timedelta(seconds=data['expires_in'])
                token_record.save()
            else:
                raise Exception("Failed to refresh access token")

    except CalendlyToken.DoesNotExist:
        pass

    token_record = CalendlyToken.objects.get(user=coach.user)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token_record.access_token}',
    }
    return headers

def make_calendly_get_request(coach, endpoint, params=None, retries=21):
    try:
        base_url = env.str("CALENDLY_BASE_URL")
        url = f"{base_url}{endpoint}"
        headers = calendly_get_header(coach)
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429 and retries > 0:
            time.sleep(3)
            return make_calendly_get_request(coach, endpoint, params, retries=retries - 1)
    except:
        pass