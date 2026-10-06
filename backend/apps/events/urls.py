"""
URL routes for Events API.
"""

from rest_framework.routers import DefaultRouter
from .views import EventViewSet

app_name = 'events'

router = DefaultRouter()
router.register(r'', EventViewSet, basename='event')

urlpatterns = router.urls
