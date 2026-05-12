from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ws/messaging/<conv_id>/ — real-time chat in a specific conversation
    re_path(r'ws/messaging/(?P<conv_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    # ws/unread/ — pushes unread count to the navbar globally
    re_path(r'ws/unread/$', consumers.UnreadConsumer.as_asgi()),
]