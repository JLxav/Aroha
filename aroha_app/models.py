from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^(09\d{9}|\+639\d{9})$",
    message="Enter a valid number, e.g. 09171234567 or +639171234567.",
)
 
 
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Barangay Staff"
        VOLUNTEER = "volunteer", "Volunteer"
        REQUESTER = "requester", "Family Member / Caregiver"
 
    # first_name and last_name already come from AbstractUser
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REQUESTER)
    phone_number = models.CharField(max_length=20, blank=True, validators=[phone_validator])
    is_approved = models.BooleanField(default=False)
 
    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_approved = True
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

from django.conf import settings
from django.db import models

class HelpRequest(models.Model):
    class RequestType(models.TextChoices):
        MEDICINE = "medicine", "Medicine / Prescriptions"
        FOOD = "food", "Groceries & Meal Assistance"
        COMPANION = "companion", "Companionship / Check-in"
        OTHER = "other", "Other Assistance"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requests"
    )
    senior_name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=150)
    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.OTHER
    )
    details = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_request_type_display()} for {self.senior_name} ({self.get_status_display()})"

    @property
    def requested_by(self):
        return self.requester    