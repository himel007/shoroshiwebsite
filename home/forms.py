import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .bd_geo import DISTRICTS, DISTRICT_CHOICES
from .models import DeliveryZone, Order


BD_PHONE_RE = re.compile(r"^(?:\+?88)?01[3-9]\d{8}$")


class CheckoutForm(forms.ModelForm):
    delivery_zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.none(),
        empty_label=None,
        widget=forms.RadioSelect,
    )
    payment_plan = forms.ChoiceField(
        choices=Order.PAYMENT_PLANS,
        initial=Order.PLAN_FULL,
        required=False,
        widget=forms.RadioSelect,
    )
    emi_months = forms.TypedChoiceField(
        choices=Order.EMI_MONTHS_CHOICES,
        coerce=int,
        required=False,
        widget=forms.RadioSelect,
    )
    district = forms.ChoiceField(
        choices=[("", "Select district")] + DISTRICT_CHOICES,
        label="District",
    )
    city = forms.ChoiceField(
        choices=[("", "Select area")],
        label="Area / Upazila",
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
            "payment_plan",
            "emi_months",
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
        # Accept any valid area as a posted value; clean() checks it matches the district.
        all_areas = sorted({a for areas in DISTRICTS.values() for a in areas})
        self.fields["city"].choices = [("", "Select area")] + [(a, a) for a in all_areas]
        self.fields["district"].widget.attrs.update({"class": "shoroshi-select", "data-district-select": "1"})
        self.fields["city"].widget.attrs.update({"class": "shoroshi-select", "data-area-select": "1"})
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

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("payment_plan"):
            cleaned["payment_plan"] = Order.PLAN_FULL
        if cleaned["payment_plan"] == Order.PLAN_EMI:
            if not cleaned.get("emi_months"):
                self.add_error("emi_months", "Choose how many months you want to pay over.")
        else:
            cleaned["emi_months"] = None

        district = cleaned.get("district")
        city = cleaned.get("city")
        if district and city and city not in DISTRICTS.get(district, []):
            self.add_error("city", "Choose an area that belongs to the selected district.")
        return cleaned


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


class OrderTrackingForm(forms.Form):
    order_number = forms.CharField(
        label="Order number",
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "e.g. SH-000123"}),
    )
    phone = forms.CharField(
        label="Phone number",
        max_length=20,
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "01XXXXXXXXX"}
        ),
    )

    def clean_order_number(self):
        raw = self.cleaned_data["order_number"]
        digits = re.sub(r"\D", "", raw)
        if not digits:
            raise forms.ValidationError("Enter your order number, for example SH-000123.")
        return int(digits)

    def clean_phone(self):
        phone = re.sub(r"[\s-]", "", self.cleaned_data["phone"])
        if not BD_PHONE_RE.match(phone):
            raise forms.ValidationError("Enter the Bangladeshi mobile number used on the order.")
        return phone[-11:]

    def find_order(self):
        """Return the matching order, or None. Call only on a valid form."""
        from .models import Order

        return (
            Order.objects.filter(
                pk=self.cleaned_data["order_number"],
                phone=self.cleaned_data["phone"],
            )
            .first()
        )
