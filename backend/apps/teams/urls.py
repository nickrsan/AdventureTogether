"""
URL routes for Teams API.
"""

from rest_framework.routers import DefaultRouter
from .views import TeamViewSet

app_name = 'teams'

router = DefaultRouter()
router.register(r'', TeamViewSet, basename='team')

urlpatterns = router.urls
