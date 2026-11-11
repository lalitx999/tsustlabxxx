from django.db import models


class Contact(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, default='unread')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contacts'


class Partner(models.Model):
    business_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'partners'
