from django.urls import path
from .views import (
    ConversationListView,
    RedeemPayTokenView,
    StartConversationView,
    MessageListView,
    SendMessageView,
    SendOfferView,
    RespondOfferView,
    UnreadCountView,
)

urlpatterns = [
    # Conversations
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/start/", StartConversationView.as_view(), name="start-conversation"),

    # Messages
    path("conversations/<int:conv_id>/messages/", MessageListView.as_view(), name="message-list"),
    path("conversations/<int:conv_id>/send/", SendMessageView.as_view(), name="send-message"),

    # Offers — sent inside a conversation by the expert
    path("conversations/<int:conv_id>/offer/", SendOfferView.as_view(), name="send-offer"),

    # Offer response — buyer accepts or declines
    path("offers/<int:offer_id>/respond/", RespondOfferView.as_view(), name="respond-offer"),
    path("pay-token/redeem/", RedeemPayTokenView.as_view()),

    # Unread badge count
    path("unread-count/", UnreadCountView.as_view(), name="unread-count"),
]