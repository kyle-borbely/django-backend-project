from django.contrib.auth import get_user_model, forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from django import forms as django_forms

User = get_user_model()


class UserChangeForm(forms.UserChangeForm):
    user_type = django_forms.ChoiceField(
        choices=(
            ("Admin", "Admin"),
            ("Super Admin", "Super Admin"),
            ("Client", "Client"),
            ("Coach", "Coach"),
            ("Coachee", "Coachee"),
        ),
        initial="admin",
        label="Role",
        widget=django_forms.Select(
            attrs={"readonly": "readonly", "style": "pointer-events: none;"}
        ),
    )

    class Meta(forms.UserChangeForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        if self.instance.pk:  # Check if the form is in edit mode
            self.fields["email"].disabled = True
            self.fields["user_type"].initial = self.instance.user_type


class UserCreationForm(forms.UserCreationForm):
    user_type = django_forms.ChoiceField(
        choices=(("Admin", "Admin"),),
        initial="Admin",
        label="Role",
        widget=django_forms.Select(
            attrs={"readonly": "readonly", "style": "pointer-events: none;"}
        ),
    )
    password1 = django_forms.CharField(
        label=_("Password"),
        strip=False,
        widget=django_forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        required=False,
    )
    password2 = django_forms.CharField(
        label=_("Password confirmation"),
        widget=django_forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        required=False,
    )
    error_message = forms.UserCreationForm.error_messages.update(
        {"duplicate_username": _("This username has already been taken.")}
    )

    def clean_first_name(self):
        first_name = self.cleaned_data["first_name"]
        if not first_name:
            raise ValidationError(_("First name field is required."))
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data["last_name"]
        if not last_name:
            raise ValidationError(_("Last name field is required."))
        return last_name

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email.lower()).exists():
            raise ValidationError(_("This email has already been taken."))
        return email

    def clean_contact_number(self):
        contact_number = self.cleaned_data["contact_number"]
        if not contact_number:
            raise ValidationError(_("Contact number field is required."))
        return contact_number

    class Meta(forms.UserCreationForm.Meta):
        model = User
        fields = ["first_name", "last_name", "email", "contact_number", "user_type"]

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise ValidationError(self.error_messages["duplicate_username"])
