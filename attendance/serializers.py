# attendance/serializers.py
from rest_framework import serializers
from .models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'first_name', 'last_name', 'email',
                  'phone_number', 'role', 'department', 'signature', 'time_posted']