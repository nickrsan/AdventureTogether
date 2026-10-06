"""
URL routes for Ephemeral Location API.
"""

from django.urls import path
from .views import ping_location, get_active_locations

app_name = 'locations'

urlpatterns = [
    path('ping/', ping_location, name='location-ping'),
    path('active/', get_active_locations, name='location-active'),
]
