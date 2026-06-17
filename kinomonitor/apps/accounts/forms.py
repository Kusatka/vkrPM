from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Subscription


class RegisterForm(UserCreationForm):
    pass


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ["movie", "cinema", "max_price", "telegram_chat_id"]
        widgets = {
            "movie": forms.Select(attrs={"class": "form-select"}),
            "cinema": forms.Select(attrs={"class": "form-select"}),
            "max_price": forms.NumberInput(attrs={"class": "form-control"}),
            "telegram_chat_id": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        data = super().clean()
        if not data.get("movie") and not data.get("cinema"):
            raise forms.ValidationError("Укажите фильм и/или кинотеатр.")
        return data
