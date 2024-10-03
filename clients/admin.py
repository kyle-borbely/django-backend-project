from django.contrib import admin
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Client
from django.utils.html import format_html
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.db import IntegrityError
from calm_darkness_38642.utils import send_email

from home.storage_backends import generate_presigned_url

User = get_user_model()


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # specify the fields to be displayed in the add form
    add_fields = ("client_name", "email", "industry")
    list_display = ["client_name", "industry", "email", "city", "user_type"]
    search_fields = ["client_name", "industry", "email", "city"]
    list_display_links = None

    def client_name(self, obj):
        return obj.client_name

    client_name.admin_order_field = "client_name"
    readonly_fields = ()

    change_fields = (
        "get_profile_picture",
        "client_name",
        "industry",
        "email",
        "city",
        "zip_code",
        "contact_name",
        "contact_number",
        "company_employees",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:
            # add the fields you want to make read-only
            readonly_fields += [
                "get_profile_picture",
                "email",
            ]
        return readonly_fields

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            presigned_url = generate_presigned_url(obj.profile_picture.name)
            return format_html(
                '<img src="{}" width="100" height="100" />', presigned_url
            )
        else:
            return "No image available"

    get_profile_picture.short_description = "Profile Picture"

    @transaction.atomic()
    def save_model(self, request, obj, form, change):
        try:
            if not change:
                normalize_email = obj.email.lower()
                # Check if email already exists in User model
                if User.objects.filter(email=normalize_email).exists():
                    raise IntegrityError(f"Email '{normalize_email}' already exists.")

                # Create a new User with user_type='Client'
                password = User.objects.make_random_password()
                user = User.objects.create_user(
                    username=normalize_email,
                    email=normalize_email,
                    password=password,
                    user_type="Client",
                    is_new_user=True,
                )

                current_site = Site.objects.get_current()
                login_url = f"https://{current_site.domain}"

                subject = "[Sloan Leaders] Client Account Created"
                username = user.username
                context = {
                    "username": username,
                    "password": password,
                    "login_url": login_url,
                }
                html_content = render_to_string("clients_email.html", context)
                response = send_email(user.email, subject, html_content)

                if not response:
                    # rollback the transaction and show error message
                    transaction.set_rollback(True)
                    # show error message
                    messages.set_level(request, messages.ERROR)
                    messages.error(
                        request, "Error: Email could not be sent. Client not created."
                    )
                else:
                    # Assign the user_type of the Client and save the object
                    obj.user = user
                    obj.email = normalize_email
                    obj.save()

            else:
                # If it's an update, just save the object
                obj.save()
        except IntegrityError as e:
            messages.set_level(request, messages.ERROR)
            messages.error(request, str(e))
            return

    # override the add_view method
    def add_view(self, request, form_url="", extra_context=None):
        # display only the fields specified in add_fields
        self.fields = self.add_fields
        extra_context = extra_context or {}
        app_label, model_name = self.model._meta.app_label, self.model._meta.model_name
        extra_context["title"] = "Add {model_name}".format(
            model_name=model_name.capitalize()
        )
        extra_context["show_save"] = True
        extra_context["save_label"] = "Save"
        extra_context["show_save_and_add_another"] = True
        return super().add_view(request, form_url, extra_context)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        try:
            search_term_as_int = int(search_term)
            queryset |= self.model.objects.filter(id=search_term_as_int)
        except ValueError:
            pass
        return queryset, use_distinct

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Search Clients"
        return super().changelist_view(request, extra_context=extra_context)

    list_display_links = ("email",)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self.fields = self.change_fields
        extra_context = extra_context or {}
        extra_context["title"] = "Client detail"
        # Customize the submit buttons
        extra_context["show_save"] = True
        extra_context["show_save_as_new"] = False
        extra_context["show_save_and_add_another"] = False
        extra_context["show_delete_link"] = True

        # Override the submit button labels
        extra_context["save_label"] = "Save"
        return super().change_view(request, object_id, form_url, extra_context)
