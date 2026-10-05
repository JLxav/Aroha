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
 
    role = forms.ChoiceField(choices = ROLE_CHOICES, label = "I am a")
    password = forms.CharField(widget = forms.PasswordInput, label = "Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label = "Confirm password")
 
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username"]
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
 
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
        if commit:
            user.save()
        return user
 
 
class ApprovedAuthenticationForm(AuthenticationForm):
    """Blocks login until an admin has approved the account."""
 
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_approved:
            raise forms.ValidationError(
                "Your account is still waiting for admin approval.",
                code="not_approved",
            )