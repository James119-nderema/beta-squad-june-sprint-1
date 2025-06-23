from rest_framework import viewsets, views
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Employee
from .serializers import EmployeeSerializer
import pandas as pd
from django.http import HttpResponse

# Set Matplotlib backend before importing plt
import matplotlib

matplotlib.use('Agg')  # Must be before any matplotlib imports
import matplotlib.pyplot as plt
import io
import time
import os
from django.conf import settings
from collections import Counter


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for employees
    """
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


# Define a cache directory for chart images
CHART_CACHE_DIR = os.path.join(settings.MEDIA_ROOT, 'chart_cache')
os.makedirs(CHART_CACHE_DIR, exist_ok=True)


def get_cached_chart(chart_type, cache_timeout=60):
    """Helper function to get or generate a cached chart"""
    cache_key = f'chart_{chart_type}_{int(time.time() / cache_timeout)}'
    cache_path = os.path.join(CHART_CACHE_DIR, f'{cache_key}.png')

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            return f.read()

    return None


def save_cached_chart(chart_type, image_data, cache_timeout=60):
    """Save chart image to cache"""
    cache_key = f'chart_{chart_type}_{int(time.time() / cache_timeout)}'
    cache_path = os.path.join(CHART_CACHE_DIR, f'{cache_key}.png')

    # Clean up old cache files
    for file in os.listdir(CHART_CACHE_DIR):
        if file.startswith(f'chart_{chart_type}_') and not file.startswith(cache_key):
            try:
                os.remove(os.path.join(CHART_CACHE_DIR, file))
            except:
                pass

    with open(cache_path, 'wb') as f:
        f.write(image_data)


class DataAnalysisView(views.APIView):
    """
    A view for analyzing attendance data
    """

    def get(self, request, format=None):
        employees = Employee.objects.all().values()
        if not employees:
            return Response({
                'total_records': 0,
                'message': 'No data available'
            })

        df = pd.DataFrame(employees)

        # Total records
        total_records = len(df)

        # Check-in vs Check-out
        checkin_vs_checkout = {}
        if 'signature' in df.columns:
            checkin_vs_checkout = df['signature'].value_counts().to_dict()

        # Department distribution
        department_distribution = {}
        if 'department' in df.columns:
            department_distribution = df['department'].value_counts().to_dict()

        # Role distribution
        role_distribution = {}
        if 'role' in df.columns:
            role_distribution = df['role'].value_counts().to_dict()

        # Daily attendance
        daily_attendance = {}
        if 'time_posted' in df.columns:
            df['date'] = pd.to_datetime(df['time_posted']).dt.date
            daily_counts = df.groupby('date').size()
            daily_attendance = {str(date): count for date, count in daily_counts.items()}

        return Response({
            'total_records': total_records,
            'checkin_vs_checkout': checkin_vs_checkout,
            'department_distribution': department_distribution,
            'role_distribution': role_distribution,
            'daily_attendance': daily_attendance
        })


class DataVisualizationView(views.APIView):
    """
    A view for visualizing attendance data - now returns all charts in one image
    """

    def get(self, request, format=None):
        # Try to get from cache first
        cached_chart = get_cached_chart('combined')
        if cached_chart:
            return HttpResponse(cached_chart, content_type='image/png')

        try:
            employees = Employee.objects.all().values()
            df = pd.DataFrame(employees)

            # Create a figure with subplots - 2x2 grid for better organization
            fig, axs = plt.subplots(2, 2, figsize=(15, 12))

            # 1. Department distribution pie chart (top-left)
            if not df.empty and 'department' in df.columns:
                dept_counts = df['department'].value_counts()
                if not dept_counts.empty:
                    axs[0, 0].pie(dept_counts, autopct='%1.1f%%', startangle=90, shadow=True)
                    axs[0, 0].set_title('Department Distribution')
                    axs[0, 0].legend(dept_counts.index, loc="center left", bbox_to_anchor=(1, 0.5))
                else:
                    axs[0, 0].text(0.5, 0.5, 'No department data', ha='center', va='center')
            else:
                axs[0, 0].text(0.5, 0.5, 'No data available', ha='center', va='center')

            # 2. Role distribution pie chart (top-right)
            if not df.empty and 'role' in df.columns:
                role_counts = df['role'].value_counts()
                if not role_counts.empty:
                    axs[0, 1].pie(role_counts, autopct='%1.1f%%', startangle=90, shadow=True)
                    axs[0, 1].set_title('Role Distribution')
                    axs[0, 1].legend(role_counts.index, loc="center left", bbox_to_anchor=(1, 0.5))
                else:
                    axs[0, 1].text(0.5, 0.5, 'No role data', ha='center', va='center')
            else:
                axs[0, 1].text(0.5, 0.5, 'No data available', ha='center', va='center')

            # 3. Daily attendance bar chart (bottom-left)
            if not df.empty and 'time_posted' in df.columns:
                try:
                    df['date'] = pd.to_datetime(df['time_posted']).dt.date
                    daily_counts = df.groupby('date').size()

                    # If we have many days, show just the last 10 days for readability
                    if len(daily_counts) > 10:
                        daily_counts = daily_counts.tail(10)

                    # Convert dates to strings for plotting
                    daily_counts.index = [date.strftime('%Y-%m-%d') for date in daily_counts.index]

                    bars = daily_counts.plot(kind='bar', ax=axs[1, 0], color='skyblue')
                    axs[1, 0].set_title('Daily Attendance (Recent Days)')
                    axs[1, 0].set_xlabel('Date')
                    axs[1, 0].set_ylabel('Count')
                    axs[1, 0].tick_params(axis='x', rotation=45)

                    # Add value labels on top of each bar
                    for bar in bars.patches:
                        height = bar.get_height()
                        axs[1, 0].text(
                            bar.get_x() + bar.get_width() / 2.,
                            height + 0.3,
                            f'{int(height)}',
                            ha='center', va='bottom'
                        )
                except Exception as e:
                    print(f"Error generating daily attendance chart: {e}")
                    axs[1, 0].text(0.5, 0.5, f'Error generating chart: {str(e)}', ha='center', va='center')
            else:
                axs[1, 0].text(0.5, 0.5, 'No attendance data', ha='center', va='center')

            # 4. Check-in vs Check-out donut chart (bottom-right)
            if not df.empty and 'signature' in df.columns:
                try:
                    signature_counts = df['signature'].value_counts()
                    if not signature_counts.empty:
                        # Create a donut chart (pie chart with a hole)
                        axs[1, 1].pie(signature_counts, labels=signature_counts.index, autopct='%1.1f%%',
                                      startangle=90, shadow=True, wedgeprops={'edgecolor': 'white'})
                        # Draw a white circle in the middle to make it a donut chart
                        centre_circle = plt.Circle((0, 0), 0.5, fc='white')
                        axs[1, 1].add_artist(centre_circle)
                        axs[1, 1].set_title('Check-in vs Check-out')
                    else:
                        axs[1, 1].text(0.5, 0.5, 'No signature data', ha='center', va='center')
                except Exception as e:
                    axs[1, 1].text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center')
            else:
                axs[1, 1].text(0.5, 0.5, 'No signature data', ha='center', va='center')

            # Adjust layout to prevent overlapping
            plt.tight_layout()

            # Save the figure to a buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close()

            # Get the image data and cache it
            buf.seek(0)
            chart_data = buf.getvalue()
            save_cached_chart('combined', chart_data)

            # Return the figure as an HTTP response
            return HttpResponse(chart_data, content_type='image/png')

        except Exception as e:
            # Return a simple error image if chart generation fails
            plt.figure(figsize=(6, 4))
            plt.text(0.5, 0.5, f"Error generating charts: {str(e)}",
                     ha='center', va='center', fontsize=12, wrap=True)
            plt.axis('off')

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)

            return HttpResponse(buf.getvalue(), content_type='image/png')


@api_view(['GET'])
def department_chart(request):
    # Try to get from cache first
    cached_chart = get_cached_chart('departments')
    if cached_chart:
        return HttpResponse(cached_chart, content_type='image/png')

    # Generate chart if not in cache
    try:
        employees = Employee.objects.all().values()
        df = pd.DataFrame(employees)

        plt.figure(figsize=(10, 8))

        if not df.empty and 'department' in df.columns:
            dept_counts = df['department'].value_counts()
            if not dept_counts.empty:
                plt.pie(dept_counts, autopct='%1.1f%%', startangle=90, shadow=True)
                plt.title('Department Distribution', fontsize=16)
                # Add legend with larger font
                plt.legend(dept_counts.index, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=12)
            else:
                plt.text(0.5, 0.5, 'No department data', ha='center', va='center', fontsize=14)
        else:
            plt.text(0.5, 0.5, 'No data available', ha='center', va='center', fontsize=14)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()

        # Get the image data and cache it
        buf.seek(0)
        chart_data = buf.getvalue()
        save_cached_chart('departments', chart_data)

        return HttpResponse(chart_data, content_type='image/png')
    except Exception as e:
        # Return a simple error image if chart generation fails
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, f"Error generating chart: {str(e)}",
                 ha='center', va='center', fontsize=12, wrap=True)
        plt.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        return HttpResponse(buf.getvalue(), content_type='image/png')


@api_view(['GET'])
def role_chart(request):
    # Try to get from cache first
    cached_chart = get_cached_chart('roles')
    if cached_chart:
        return HttpResponse(cached_chart, content_type='image/png')

    # Generate chart if not in cache
    try:
        employees = Employee.objects.all().values()
        df = pd.DataFrame(employees)

        plt.figure(figsize=(10, 8))

        if not df.empty and 'role' in df.columns:
            role_counts = df['role'].value_counts()
            if not role_counts.empty:
                plt.pie(role_counts, autopct='%1.1f%%', startangle=90, shadow=True)
                plt.title('Role Distribution', fontsize=16)
                # Add legend with larger font
                plt.legend(role_counts.index, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=12)
            else:
                plt.text(0.5, 0.5, 'No role data', ha='center', va='center', fontsize=14)
        else:
            plt.text(0.5, 0.5, 'No data available', ha='center', va='center', fontsize=14)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()

        # Get the image data and cache it
        buf.seek(0)
        chart_data = buf.getvalue()
        save_cached_chart('roles', chart_data)

        return HttpResponse(chart_data, content_type='image/png')
    except Exception as e:
        # Return a simple error image if chart generation fails
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, f"Error generating chart: {str(e)}",
                 ha='center', va='center', fontsize=12, wrap=True)
        plt.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        return HttpResponse(buf.getvalue(), content_type='image/png')


@api_view(['GET'])
def attendance_chart(request):
    # Try to get from cache first
    cached_chart = get_cached_chart('attendance')
    if cached_chart:
        return HttpResponse(cached_chart, content_type='image/png')

    # Generate chart if not in cache
    try:
        employees = Employee.objects.all().values()
        df = pd.DataFrame(employees)

        plt.figure(figsize=(12, 8))

        if not df.empty and 'time_posted' in df.columns:
            try:
                df['date'] = pd.to_datetime(df['time_posted']).dt.date
                daily_counts = df.groupby('date').size()

                # If we have many days, show just the last 10 days for readability
                if len(daily_counts) > 10:
                    daily_counts = daily_counts.tail(10)

                daily_counts.index = [date.strftime('%Y-%m-%d') for date in daily_counts.index]
                bars = plt.bar(daily_counts.index, daily_counts.values, color='skyblue')
                plt.title('Daily Attendance (Recent Days)', fontsize=16)
                plt.xlabel('Date', fontsize=14)
                plt.ylabel('Count', fontsize=14)
                plt.xticks(rotation=45, fontsize=12)
                plt.yticks(fontsize=12)

                # Add value labels
                for bar in bars:
                    height = bar.get_height()
                    plt.text(
                        bar.get_x() + bar.get_width() / 2.,
                        height + 0.3,
                        f'{int(height)}',
                        ha='center', va='bottom',
                        fontsize=12
                    )
            except Exception as e:
                plt.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', fontsize=14)
        else:
            plt.text(0.5, 0.5, 'No attendance data', ha='center', va='center', fontsize=14)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()

        # Get the image data and cache it
        buf.seek(0)
        chart_data = buf.getvalue()
        save_cached_chart('attendance', chart_data)

        return HttpResponse(chart_data, content_type='image/png')
    except Exception as e:
        # Return a simple error image if chart generation fails
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, f"Error generating chart: {str(e)}",
                 ha='center', va='center', fontsize=12, wrap=True)
        plt.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        return HttpResponse(buf.getvalue(), content_type='image/png')


@api_view(['GET'])
def signature_chart(request):
    # Try to get from cache first
    cached_chart = get_cached_chart('signatures')
    if cached_chart:
        return HttpResponse(cached_chart, content_type='image/png')

    # Generate chart if not in cache
    try:
        employees = Employee.objects.all().values()
        df = pd.DataFrame(employees)

        plt.figure(figsize=(10, 8))

        if not df.empty and 'signature' in df.columns:
            try:
                signature_counts = df['signature'].value_counts()
                if not signature_counts.empty:
                    plt.pie(signature_counts, labels=signature_counts.index, autopct='%1.1f%%',
                            startangle=90, shadow=True, wedgeprops={'edgecolor': 'white'}, textprops={'fontsize': 14})
                    # Draw a white circle to make it a donut chart
                    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
                    plt.gca().add_artist(centre_circle)
                    plt.title('Check-in vs Check-out', fontsize=16)
                else:
                    plt.text(0.5, 0.5, 'No signature data', ha='center', va='center', fontsize=14)
            except Exception as e:
                plt.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', fontsize=14)
        else:
            plt.text(0.5, 0.5, 'No signature data', ha='center', va='center', fontsize=14)

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()

        # Get the image data and cache it
        buf.seek(0)
        chart_data = buf.getvalue()
        save_cached_chart('signatures', chart_data)

        return HttpResponse(chart_data, content_type='image/png')
    except Exception as e:
        # Return a simple error image if chart generation fails
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, f"Error generating chart: {str(e)}",
                 ha='center', va='center', fontsize=12, wrap=True)
        plt.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        return HttpResponse(buf.getvalue(), content_type='image/png')