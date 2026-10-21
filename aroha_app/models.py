from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


# ==========================================
# Validators
# ==========================================

# Validates Philippine mobile number formats (e.g., 09171234567 or +639171234567)
phone_validator = RegexValidator(
    regex=r"^(09\d{9}|\+639\d{9})$",
    message="Enter a valid number, e.g. 09171234567 or +639171234567.",
)


# ==========================================
# Custom User Model
# ==========================================

class User(AbstractUser):
    """Custom user model supporting multi-role access, admin approval, and 2FA setting."""

    # Account Role Choices
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Barangay Staff"
        VOLUNTEER = "volunteer", "Volunteer"
        REQUESTER = "requester", "Requester"

    # User Role & Account Flags
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REQUESTER)
    phone_number = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    is_approved = models.BooleanField(default=False)  # Admin/staff approval flag
    is_rejected = models.BooleanField(default=False)  # Registration rejection flag
    email = models.EmailField(blank=True, null=True)   # Email for notifications and 2FA
    is_otp_enabled = models.BooleanField(default=True)  # Enables 2FA email verification on login

    def save(self, *args, **kwargs):
        # Superuser defaults
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_approved = True
            self.is_staff = True

        # Keep is_staff in sync with role
        if self.role in [self.Role.STAFF, self.Role.ADMIN]:
            self.is_staff = True
        else:
            if not self.is_superuser:
                self.is_staff = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


# ==========================================
# Help Request Model
# ==========================================

class HelpRequest(models.Model):
    """Stores assistance requests created by family members for seniors."""

    # Categorization Choices
    class RequestType(models.TextChoices):
        MEDICINE = "medicine", "Medicine / Prescriptions"
        FOOD = "food", "Groceries & Meal Assistance"
        COMPANION = "companion", "Companionship / Check-in"
        OTHER = "other", "Other Assistance"

    # Lifecycle Status Choices
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    # Related Account Connections
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requests"  # Family member who submitted the request
    )
    assigned_volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests"  # Volunteer assigned to assist
    )

    # Beneficiary & Contact Information
    senior_name = models.CharField(max_length=150)    # Name of the senior receiving assistance
    contact_person = models.CharField(max_length=150) # Point of contact for coordination

    # Location Information
    house_number = models.CharField(max_length=50, default="")
    street = models.CharField(max_length=100, blank=True, null=True)
    barangay = models.CharField(max_length=100, default="")
    city = models.CharField(max_length=100, default="Davao City")

    # Details & Status Tracking
    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.OTHER
    )
    details = models.TextField()  # Specific assistance details
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    rejection_reason = models.TextField(blank=True)  # Reason provided if rejected by staff

    # Volunteer Performance Feedback
    volunteer_rating = models.PositiveSmallIntegerField(null=True, blank=True)  # Star/numeric rating
    volunteer_feedback = models.TextField(blank=True)  # Written review from requester

    # Audit Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # Show newest requests first

    def __str__(self):
        return f"{self.get_request_type_display()} for {self.senior_name} ({self.get_status_display()})"

    @property
    def full_location(self):
        """Returns a nicely formatted full address string."""
        street_part = f"{self.street}, " if self.street else ""
        return f"{self.house_number} {street_part}{self.barangay}, {self.city}"

    @property
    def requested_by(self):
        """Alias returning the user model object who submitted the request."""
        return self.requester