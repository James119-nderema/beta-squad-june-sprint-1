# attendance/models.py
from django.db import models

class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=False)
    phone_number = models.CharField(max_length=15)
    role = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    signature = models.TextField(blank=True)
    time_posted = models.DateTimeField(auto_now_add=True)  # Adds timestamp when record is created

    def __str__(self):
        return f"{self.first_name} {self.last_name}"