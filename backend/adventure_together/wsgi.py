"""
WSGI config for AdventureTogether project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adventure_together.settings')

application = get_wsgi_application()
