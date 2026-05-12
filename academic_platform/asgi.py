"""
ASGI config for academic_platform project.

Handles both HTTP (via Django) and WebSocket (via Django Channels + Redis).

Start command on Railway:
    daphne -b 0.0.0.0 -p $PORT academic_platform.asgi:application
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messaging.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academic_platform.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})