from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from .models import TermAndCondition


class TermAndConditionForm(forms.ModelForm):
    body = forms.CharField(widget=CKEditorUploadingWidget())

    class Meta:
        model = TermAndCondition
        fields = "__all__"
