"""
URL routes for Quests API.
"""

from rest_framework.routers import DefaultRouter
from .views import QuestViewSet

app_name = 'quests'

router = DefaultRouter()
router.register(r'', QuestViewSet, basename='quest')

urlpatterns = router.urls
