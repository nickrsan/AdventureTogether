"""
Core health check and service status views.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Returns system status, active database backend, and service health metrics.
    """
    database_ok = True
    db_backend = connection.settings_dict.get('ENGINE', 'unknown')

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
    except Exception as e:
        database_ok = False

    return Response({
        'status': 'healthy' if database_ok else 'degraded',
        'service': 'AdventureTogether Backend API',
        'database_connected': database_ok,
        'database_engine': db_backend,
        'version': '1.0.0'
    })
