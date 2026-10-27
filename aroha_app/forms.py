from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import HelpRequest, User

# ==========================================
# Authentication & User Registration Forms
# ==========================================


class SignUpForm(forms.ModelForm):
    """Registration form for new Voluteer and Requester user accounts."""

    # Only Volunteer and Requester roles can be selected at registration.
    # Barangay Staff and Admin accounts are managed via the admin panel.
    ROLE_CHOICES = [
        ("", "Select your role"),
        (User.Role.VOLUNTEER, "Volunteer"),
        (User.Role.REQUESTER, "Requester"),
    ]

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"placeholder": "name@example.com", "class": "form-control"}
        ),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="I am a")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, label="Confirm password"
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "phone_number",
        ]
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
    """Custom login form that strictly verifies user account approval and rejection status."""

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            # 1. Lookup user record to verify account status flags BEFORE authentication
            user = User.objects.filter(username=username).first()

            if user and user.check_password(password):
                if not user.is_active:
                    raise forms.ValidationError(
                        "This account has been deactivated. Please contact an administrator.",
                        code="deactivated",
                    )
                if user.is_rejected:
                    raise forms.ValidationError(
                        "Your account registration has been rejected by Barangay staff.",
                        code="rejected",
                    )
                if not user.is_approved:
                    raise forms.ValidationError(
                        "Your account is awaiting Barangay staff approval.",
                        code="unapproved",
                    )

            # 2. Perform standard Django authentication
            self.user_cache = authenticate(
                self.request, username=username, password=password
            )

            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


# ==========================================
# Help Request & Service Workflow Forms
# ==========================================


# Comprehensive list of Davao City Barangays
DAVAO_BARANGAYS = [
    "Agdao", "Alambre", "Alejandra Navarro (Lasang)", "Alfonso Angliongto Sr.",
    "Bago Aplaya", "Bago Gallera", "Bago Oshiro", "Baguio", "Baliok", "Bangkas Heights",
    "Bayanihan", "Bucana", "Buhangin", "Bunawan", "Cabantian", "Calinan", "Carmen",
    "Catalunan Grande", "Catalunan Pequeño", "Centro (San Juan)", "Communal", "Crossing Bayabas",
    "Dacudao", "Daliao", "Daliaon Plantation", "Datu Salumay", "Dumoy", "Eden", "El Rio",
    "Gatungan", "Gov. Paciano Bangoy", "Gov. Vicente Duterte", "Gumalang", "Ilang",
    "Indangan", "Kapitan Tomas Monteverde Sr.", "Kilate", "Lamanan", "Lapu-Lapu",
    "Leon Garcia", "Lizada", "Los Amigos", "Lumiad", "Ma-a", "Mabuhay", "Magsaysay",
    "Mahayag", "Malabog", "Malagos", "Manambulan", "Mandug", "Manuel Guianga", "Marapangi",
    "Marilog", "Matina Aplaya", "Matina Biao", "Matina Crossing", "Matina Pangi", "Mintal",
    "Muñoz", "Pampanga", "Panacan", "Pangyan", "Paquibato", "Poblacion", "R. Castillo",
    "Riverside", "Saloy", "San Antonio", "San Isidro", "San Rafael", "Santa Ana", "Sasa",
    "Sirawan", "Sirib", "Subasta", "Suawan", "Suazo", "Tacunan", "Tagakpan", "Tagluno",
    "Tagurano", "Talandang", "Talomo", "Tamu-an", "Tark", "Tibuloy", "Tibungco", "Tigatto",
    "Toril", "Tugbok", "Tugbok Proper", "Ula", "Vicente Hizon Sr.", "Waan", "Wangan", "Wines"
]

class HelpRequestForm(forms.ModelForm):
    """Form for requesters to submit senior assistance requests."""

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
            "details",
        ]
        widgets = {
            "house_number": forms.TextInput(
                attrs={"placeholder": "House/Block/Lot No."}
            ),
            "street": forms.TextInput(
                attrs={"placeholder": "Street name (optional)"}
            ),
            "barangay": forms.TextInput(
                attrs={
                    "placeholder": "Barangay",
                    "list": "davao-barangays",  # Connects field to the datalist
                    "autocomplete": "off",
                }
            ),
            "city": forms.TextInput(
                attrs={"placeholder": "City / Municipality"}
            ),
        }


class BarangayStatusForm(forms.ModelForm):
    """Form for Barangay staff to update request statuses and provide rejection reasons."""

    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Explain why this request is being rejected",
            }
        ),
    )

    class Meta:
        model = HelpRequest
        fields = ["status", "rejection_reason"]
        widgets = {
            "status": forms.Select(attrs={"class": "status-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("status") == HelpRequest.Status.REJECTED
            and not cleaned.get("rejection_reason", "").strip()
        ):
            self.add_error(
                "rejection_reason",
                "Please provide a reason for rejecting this request.",
            )
        return cleaned


class VolunteerFeedbackForm(forms.ModelForm):
    """Form for requesters to submit ratings and feedback for volunteers."""

    class Meta:
        model = HelpRequest
        fields = ["volunteer_rating", "volunteer_feedback"]
        labels = {
            "volunteer_rating": "How was your experience with the volunteer?",
            "volunteer_feedback": "Additional comments",
        }
        widgets = {
            "volunteer_rating": forms.Select(
                choices=[
                    ("", "Select a rating"),
                    (1, "1 - Poor"),
                    (2, "2 - Fair"),
                    (3, "3 - Good"),
                    (4, "4 - Very good"),
                    (5, "5 - Excellent"),
                ]
            ),
            "volunteer_feedback": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Share more about your experience (optional)",
                }
            ),
        }

    def clean_volunteer_rating(self):
        rating = self.cleaned_data["volunteer_rating"]
        if rating is None or not 1 <= rating <= 5:
            raise forms.ValidationError("Choose a rating from 1 to 5.")
        return rating