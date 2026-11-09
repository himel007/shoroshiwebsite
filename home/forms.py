import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import DeliveryZone, Order


BD_PHONE_RE = re.compile(r"^(?:\+?88)?01[3-9]\d{8}$")


class CheckoutForm(forms.ModelForm):
    delivery_zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.none(),
        empty_label=None,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Order
        fields = [
            "full_name",
            "phone",
            "email",
            "address_line1",
            "address_line2",
            "city",
            "district",
            "postcode",
            "delivery_zone",
            "notes",
        ]
        widgets = {
            "address_line1": forms.TextInput(attrs={"placeholder": "House number and street name"}),
            "address_line2": forms.TextInput(attrs={"placeholder": "Apartment, floor, etc. (optional)"}),
            "notes": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Notes about your order, e.g. delivery instructions."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["delivery_zone"].queryset = DeliveryZone.objects.filter(is_active=True)
        self.fields["phone"].widget.attrs.update(
            {"inputmode": "tel", "autocomplete": "tel", "placeholder": "01XXXXXXXXX"}
        )
        autocomplete = {
            "full_name": "name",
            "email": "email",
            "address_line1": "address-line1",
            "address_line2": "address-line2",
            "city": "address-level2",
            "district": "address-level1",
            "postcode": "postal-code",
        }
        for name, value in autocomplete.items():
            self.fields[name].widget.attrs["autocomplete"] = value

    def clean_phone(self):
        phone = re.sub(r"[\s-]", "", self.cleaned_data["phone"])
        if not BD_PHONE_RE.match(phone):
            raise forms.ValidationError("Enter a valid Bangladeshi mobile number, e.g. 01712345678.")
        return phone[-11:]


class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class AccountDetailsForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        others = get_user_model().objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if others.exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email
