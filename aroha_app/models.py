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