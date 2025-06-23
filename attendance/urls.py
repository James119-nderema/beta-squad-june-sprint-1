# attendance/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (EmployeeViewSet, DataAnalysisView, DataVisualizationView,
                   department_chart, role_chart, attendance_chart, signature_chart)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('analysis/', DataAnalysisView.as_view(), name='data-analysis'),
    path('visualization/', DataVisualizationView.as_view(), name='data-visualization'),
    path('chart/departments/', department_chart, name='department-chart'),
    path('chart/roles/', role_chart, name='role-chart'),
    path('chart/attendance/', attendance_chart, name='attendance-chart'),
    path('chart/signatures/', signature_chart, name='signature-chart'),
]