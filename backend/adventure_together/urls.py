"""
URL configuration for AdventureTogether project.

Routes top-level API endpoints to their respective domain applications.
"""

from django.contrib import admin
from django.urls import path, include
from apps.core.views import health_check

urlpatterns = [
    # Admin Interface
    path('admin/', admin.site.urls),

    # Health Check Endpoint
    path('api/health/', health_check, name='api-health-check'),

    # Domain Application API Endpoints
    path('api/events/', include('apps.events.urls')),
    path('api/teams/', include('apps.teams.urls')),
    path('api/quests/', include('apps.quests.urls')),
    path('api/locations/', include('apps.locations.urls')),
    path('api/submissions/', include('apps.submissions.urls')),
]
