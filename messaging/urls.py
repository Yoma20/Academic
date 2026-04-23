from django.urls import path
from .views import (
    ConversationListView,
    StartConversationView,
    MessageListView,
    SendMessageView,
    UnreadCountView,
)

urlpatterns = [
    # List all conversations for the current user
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),

    # Start a new conversation (or retrieve existing) with an optional first message
    path("conversations/start/", StartConversationView.as_view(), name="start-conversation"),

    # Get all messages in a conversation (also marks them read)
    path("conversations/<int:conv_id>/messages/", MessageListView.as_view(), name="message-list"),

    # Send a message into an existing conversation
    path("conversations/<int:conv_id>/send/", SendMessageView.as_view(), name="send-message"),

    # Unread message count (for notification badge)
    path("unread-count/", UnreadCountView.as_view(), name="unread-count"),
]
