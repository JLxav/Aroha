from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
 
from .models import User
 
 
class SignUpForm(forms.ModelForm):
    # Only these two roles can be picked at sign-up.
    # Staff and Admin accounts are created by an admin in /admin/.
    ROLE_CHOICES = [
        ("", "Select your role"),
        (User.Role.VOLUNTEER, "Volunteer"),
        (User.Role.REQUESTER, "Requester"),
    ]
 
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="I am a")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
 
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "phone_number"]
        labels = {"phone_number": "Contact number"}
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["phone_number"].required = True
        self.fields["phone_number"].widget.attrs["placeholder"] = "09171234567"
 
    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
 
        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match.")
        elif password:
            temp_user = User(username=cleaned.get("username", ""))
            try:
                validate_password(password, user=temp_user)
            except forms.ValidationError as e:
                self.add_error("password", e)
        return cleaned
 
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = self.cleaned_data["role"]
        user.is_approved = False
        user.is_rejected = False
        if commit:
            user.save()
        return user
 
 
class ApprovedAuthenticationForm(AuthenticationForm):
    """Blocks login until an admin has approved the account."""
 
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_rejected:
            raise forms.ValidationError(
                "This account was not approved. Please contact your barangay administrator.",
                code="account_rejected",
            )
        if not user.is_approved:
            raise forms.ValidationError(
                "Your account is still waiting for admin approval.",
                code="not_approved",
            )

from django import forms
from .models import HelpRequest

class HelpRequestForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = [
            "request_type", 
            "senior_name", 
            "house_number", 
            "street", 
            "barangay", 
            "city", 
            "contact_person", 
            "details"
        ]
        widgets = {
            "house_number": forms.TextInput(attrs={"placeholder": "House/Block/Lot No."}),
            "street": forms.TextInput(attrs={"placeholder": "Street name (optional)"}),
            "barangay": forms.TextInput(attrs={"placeholder": "Barangay"}),
            "city": forms.TextInput(attrs={"placeholder": "City / Municipality"}),
        }

class BarangayStatusForm(forms.ModelForm):
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Explain why this request is being rejected"}),
    )

    class Meta:
        model = HelpRequest
        fields = ["status", "rejection_reason"]
        widgets = {
            "status": forms.Select(attrs={"class": "status-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == HelpRequest.Status.REJECTED and not cleaned.get("rejection_reason", "").strip():
            self.add_error("rejection_reason", "Please provide a reason for rejecting this request.")
        return cleaned


class VolunteerFeedbackForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = ["volunteer_rating", "volunteer_feedback"]
        labels = {
            "volunteer_rating": "How was your experience with the volunteer?",
            "volunteer_feedback": "Additional comments",
        }
        widgets = {
            "volunteer_rating": forms.Select(choices=[("", "Select a rating"), (1, "1 - Poor"), (2, "2 - Fair"), (3, "3 - Good"), (4, "4 - Very good"), (5, "5 - Excellent")]),
            "volunteer_feedback": forms.Textarea(attrs={"rows": 3, "placeholder": "Share more about your experience (optional)"}),
        }

    def clean_volunteer_rating(self):
        rating = self.cleaned_data["volunteer_rating"]
        if rating is None or not 1 <= rating <= 5:
            raise forms.ValidationError("Choose a rating from 1 to 5.")
        return rating
