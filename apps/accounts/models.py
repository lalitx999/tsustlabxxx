from django.contrib.auth.models import AbstractUser
from django.db import models

# db_table names match the legacy database so existing data can be attached.


class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'branches'

    def __str__(self):
        return self.name


class StaffUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('expert', 'Expert Specialist'),
        ('front', 'Front Desk Staff'),
        ('customer', 'Customer'),
    ]
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='front')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    line_user_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    class Meta:
        db_table = 'staff_users'

    @property
    def display_name(self):
        return self.full_name or self.username

    @property
    def initials(self):
        parts = (self.full_name or self.username or 'AD').split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return parts[0][:2].upper()
