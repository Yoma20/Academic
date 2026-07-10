"""
WebSocket consumers for the messaging app.

ChatConsumer   — handles real-time messages + typing indicators in a
                 specific conversation.
UnreadConsumer — pushes unread count updates to the navbar globally,
                 and (bonus) marks the user online/offline on clean
                 connect/disconnect.

NOTE: These only do anything once the browser can actually establish
the websocket connection. Typing indicators specifically have no REST
fallback — they're inert until that connection issue is resolved.
Online/offline status does NOT depend on this file working; it's
driven by the REST heartbeat in presence.py / views.py instead.

Both consumers use Django's session-based authentication, which works
automatically because the browser sends the session cookie on WebSocket
handshake (same origin / SameSite=None + withCredentials on the client).
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import models as db_models
from .models import Conversation, Message
from .serializers import MessageSerializer
from .presence import set_online, set_offline


# ─── helpers ──────────────────────────────────────────────────────────────────

@database_sync_to_async
def get_conversation(conv_id, user):
    """Return conversation if the user is a participant, else None."""
    try:
        conv = Conversation.objects.get(pk=conv_id)
        if conv.participant_1 == user or conv.participant_2 == user:
            return conv
        return None
    except Conversation.DoesNotExist:
        return None


@database_sync_to_async
def create_message(conversation, sender, content):
    """Persist a new text message and bump conversation.updated_at."""
    msg = Message.objects.create(
        conversation=conversation,
        sender=sender,
        content=content,
        message_type="text",
    )
    conversation.save()   # bumps auto_now updated_at
    return msg


@database_sync_to_async
def serialize_message(message, request=None):
    sender = message.sender

    # Resolve avatar — same dual-system logic
    profile_picture = None
    if sender.user_type == "expert":
        try:
            profile_picture = sender.expert_profile.avatar_url or None
        except Exception:
            pass
    if not profile_picture and sender.profile_picture:
        profile_picture = sender.profile_picture.url  # relative URL is fine for WS

    return {
        "id":           message.id,
        "conversation": message.conversation_id,
        "sender": {
            "id":              sender.id,
            "username":        sender.username,
            "first_name":      sender.first_name,
            "last_name":       sender.last_name,
            "user_type":       sender.user_type,
            "profile_picture": profile_picture,
        },
        "content":      message.content,
        "message_type": message.message_type,
        "offer":        None,
        "is_read":      message.is_read,
        "is_edited":    message.is_edited,
        "is_deleted":   message.is_deleted,
        "reactions":    [],
        "created_at":   message.created_at.isoformat(),
    }

@database_sync_to_async
def get_unread_count(user):
    """Total unread messages for a user across all conversations."""
    return Message.objects.filter(
        conversation__in=Conversation.objects.filter(
            db_models.Q(participant_1=user) | db_models.Q(participant_2=user)
        ),
        is_read=False,
    ).exclude(sender=user).count()


# ─── ChatConsumer ─────────────────────────────────────────────────────────────

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Handles real-time messaging + typing indicators inside one conversation.

    Group name: chat_<conv_id>

    Client sends:
      { "content": "Hello!" }                          — regular message
      { "type": "typing", "is_typing": true }           — typing indicator

    Server pushes:
      serialized Message dict                           — new message
      { "type": "typing", "user_id": .., "is_typing": .. } — typing update
    """

    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.conv_id = self.scope["url_route"]["kwargs"]["conv_id"]
        self.conversation = await get_conversation(self.conv_id, user)

        if not self.conversation:
            await self.close(code=4003)
            return

        self.group_name = f"chat_{self.conv_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        user = self.scope["user"]
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        # ── Typing indicator (no persistence, just a relay) ──────────────────
        if data.get("type") == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "user.typing",
                    "user_id": user.id,
                    "is_typing": bool(data.get("is_typing")),
                },
            )
            return

        # ── Regular text message ──────────────────────────────────────────────
        content = (data.get("content") or "").strip()
        if not content or len(content) > 5000:
            return

        message = await create_message(self.conversation, user, content)
        payload = await serialize_message(message)

        # Broadcast to everyone in the conversation group (both participants)
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat.message", "message": payload},
        )

        # Also nudge the other participant's UnreadConsumer so their badge updates
        other = (
            self.conversation.participant_2
            if self.conversation.participant_1 == user
            else self.conversation.participant_1
        )
        unread = await get_unread_count(other)
        await self.channel_layer.group_send(
            f"unread_{other.id}",
            {"type": "unread.update", "unread_count": unread},
        )

    # Handler for group_send type "chat.message"
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    # Handler for group_send type "user.typing" — don't echo back to the sender
    async def user_typing(self, event):
        if event["user_id"] == self.scope["user"].id:
            return
        await self.send(text_data=json.dumps({
            "type": "typing",
            "user_id": event["user_id"],
            "is_typing": event["is_typing"],
        }))


# ─── UnreadConsumer ───────────────────────────────────────────────────────────

class UnreadConsumer(AsyncWebsocketConsumer):
    """
    Pushes unread-count updates to the navbar for the authenticated user.
    Also marks the user online while connected, offline on clean disconnect
    (a bonus signal on top of the REST heartbeat, which remains the primary
    source of truth for presence since it doesn't depend on this socket).

    Group name: unread_<user_id>

    Server pushes: { "unread_count": 3 }
    (The client never sends anything meaningful to this socket.)
    """

    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user_id = user.id
        self.group_name = f"unread_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await database_sync_to_async(set_online)(user.id)

        # Send the current count immediately on connect
        count = await get_unread_count(user)
        await self.send(text_data=json.dumps({"unread_count": count}))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "user_id"):
            await database_sync_to_async(set_offline)(self.user_id)

    async def receive(self, text_data):
        # Clients don't need to send anything to this socket
        pass

    # Handler for group_send type "unread.update"
    async def unread_update(self, event):
        await self.send(text_data=json.dumps({"unread_count": event["unread_count"]}))