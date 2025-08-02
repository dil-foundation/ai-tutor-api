"""
Messaging System Pydantic Schemas

This module defines all the Pydantic models for the messaging system,
including request/response models for conversations, messages, participants, and user status.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# =====================================================
# ENUMS
# =====================================================

class ConversationType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class UserStatusType(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"

class ParticipantRole(str, Enum):
    PARTICIPANT = "participant"
    ADMIN = "admin"
    MODERATOR = "moderator"

class MessageStatusType(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

# =====================================================
# CONVERSATION MODELS
# =====================================================

class ConversationCreate(BaseModel):
    """Request model for creating a new conversation"""
    title: Optional[str] = Field(None, max_length=100, description="Optional title for group conversations")
    type: ConversationType = Field(default=ConversationType.DIRECT, description="Type of conversation")
    participant_ids: List[str] = Field(..., min_items=1, max_items=50, description="List of user IDs to add to conversation")

    @validator('participant_ids')
    def validate_participants(cls, v):
        if len(v) < 1:
            raise ValueError('At least one participant is required')
        if len(v) > 50:
            raise ValueError('Maximum 50 participants allowed')
        return v

class ConversationUpdate(BaseModel):
    """Request model for updating a conversation"""
    title: Optional[str] = Field(None, max_length=100)
    is_archived: Optional[bool] = None

class ConversationResponse(BaseModel):
    """Response model for conversation data"""
    id: str
    title: Optional[str]
    type: ConversationType
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    is_archived: bool
    is_deleted: bool
    participants: List[Dict[str, Any]] = Field(default_factory=list)
    unread_count: int = Field(default=0, ge=0)
    last_message: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class ConversationListResponse(BaseModel):
    """Response model for paginated conversation list"""
    conversations: List[ConversationResponse]
    total_count: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool

# =====================================================
# MESSAGE MODELS
# =====================================================

class MessageCreate(BaseModel):
    """Request model for creating a new message"""
    content: str = Field(..., min_length=1, max_length=5000, description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    reply_to_id: Optional[str] = Field(None, description="ID of message being replied to")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional message metadata")

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class MessageUpdate(BaseModel):
    """Request model for updating a message"""
    content: str = Field(..., min_length=1, max_length=5000)

class MessageResponse(BaseModel):
    """Response model for message data"""
    id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    sender_avatar: Optional[str] = None
    content: str
    message_type: MessageType
    reply_to_id: Optional[str] = None
    reply_to_content: Optional[str] = None
    reply_to_sender_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: MessageStatusType = Field(default=MessageStatusType.SENT)
    reactions: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True

class MessageListResponse(BaseModel):
    """Response model for paginated message list"""
    messages: List[MessageResponse]
    total_count: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool

# =====================================================
# PARTICIPANT MODELS
# =====================================================

class ParticipantAdd(BaseModel):
    """Request model for adding a participant to conversation"""
    user_id: str = Field(..., description="User ID to add")
    role: ParticipantRole = Field(default=ParticipantRole.PARTICIPANT, description="Role for the participant")

class ParticipantUpdate(BaseModel):
    """Request model for updating participant settings"""
    role: Optional[ParticipantRole] = None
    is_muted: Optional[bool] = None
    is_blocked: Optional[bool] = None

class ParticipantResponse(BaseModel):
    """Response model for participant data"""
    id: str
    conversation_id: str
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    role: ParticipantRole
    joined_at: datetime
    left_at: Optional[datetime] = None
    is_muted: bool = False
    is_blocked: bool = False
    last_read_at: datetime
    is_online: bool = False
    last_seen_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ParticipantListResponse(BaseModel):
    """Response model for participant list"""
    participants: List[ParticipantResponse]
    total_count: int

# =====================================================
# USER STATUS MODELS
# =====================================================

class UserStatusUpdate(BaseModel):
    """Request model for updating user status"""
    status: UserStatusType
    is_typing: bool = Field(default=False, description="Whether user is currently typing")
    typing_in_conversation: Optional[str] = Field(None, description="Conversation ID where user is typing")

class UserStatusResponse(BaseModel):
    """Response model for user status data"""
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    status: UserStatusType
    is_typing: bool
    typing_in_conversation: Optional[str] = None
    last_seen_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserStatusListResponse(BaseModel):
    """Response model for multiple user statuses"""
    users: List[UserStatusResponse]

# =====================================================
# WEBSOCKET MODELS
# =====================================================

class WebSocketMessage(BaseModel):
    """Base model for WebSocket messages"""
    type: str
    data: Optional[Dict[str, Any]] = None

class JoinConversationMessage(BaseModel):
    """WebSocket message for joining a conversation"""
    type: str = Field(default="join_conversation")
    conversation_id: str

class LeaveConversationMessage(BaseModel):
    """WebSocket message for leaving a conversation"""
    type: str = Field(default="leave_conversation")
    conversation_id: str

class TypingMessage(BaseModel):
    """WebSocket message for typing indicators"""
    type: str
    conversation_id: str
    is_typing: bool

class MessageReadMessage(BaseModel):
    """WebSocket message for marking message as read"""
    type: str = Field(default="message_read")
    message_id: str
    conversation_id: str

class NewMessageWebSocket(BaseModel):
    """WebSocket message for new message notification"""
    type: str = Field(default="new_message")
    message: MessageResponse

class UserStatusChangeWebSocket(BaseModel):
    """WebSocket message for user status changes"""
    type: str = Field(default="user_status_change")
    user_id: str
    status: UserStatusType
    is_typing: bool
    conversation_id: Optional[str] = None

# =====================================================
# FILE UPLOAD MODELS
# =====================================================

class FileUploadResponse(BaseModel):
    """Response model for file upload"""
    message_id: str
    file_url: str
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime

class FileMetadata(BaseModel):
    """Model for file metadata"""
    filename: str
    content_type: str
    size: int
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None

# =====================================================
# PAGINATION MODELS
# =====================================================

class PaginationParams(BaseModel):
    """Request model for pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=50, ge=1, le=100, description="Number of items per page")

    @validator('limit')
    def validate_limit(cls, v):
        if v > 100:
            raise ValueError('Maximum limit is 100')
        return v

class PaginationResponse(BaseModel):
    """Response model for pagination metadata"""
    total_count: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @property
    def total_pages(self) -> int:
        return (self.total_count + self.limit - 1) // self.limit

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

# =====================================================
# ERROR MODELS
# =====================================================

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    error: str = "Validation Error"
    message: str
    field_errors: List[Dict[str, str]]
    timestamp: datetime = Field(default_factory=datetime.now)

# =====================================================
# NOTIFICATION MODELS
# =====================================================

class NotificationMessage(BaseModel):
    """Model for system notification messages"""
    type: str = Field(default="notification")
    title: str
    message: str
    level: str = Field(default="info")  # info, warning, error, success
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ConversationNotification(BaseModel):
    """Model for conversation-specific notifications"""
    conversation_id: str
    notification_type: str  # new_message, participant_added, participant_removed, etc.
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

# =====================================================
# SEARCH MODELS
# =====================================================

class MessageSearchParams(BaseModel):
    """Request model for message search"""
    query: str = Field(..., min_length=1, max_length=100)
    conversation_id: Optional[str] = None
    sender_id: Optional[str] = None
    message_type: Optional[MessageType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=50)

class MessageSearchResponse(BaseModel):
    """Response model for message search results"""
    messages: List[MessageResponse]
    total_count: int
    query: str
    page: int
    limit: int
    has_next: bool
    has_prev: bool

# =====================================================
# ANALYTICS MODELS
# =====================================================

class ConversationAnalytics(BaseModel):
    """Model for conversation analytics"""
    conversation_id: str
    total_messages: int
    total_participants: int
    active_participants: int
    last_activity: datetime
    message_types: Dict[str, int]
    average_messages_per_day: float
    most_active_hours: List[int]

class UserAnalytics(BaseModel):
    """Model for user messaging analytics"""
    user_id: str
    total_conversations: int
    total_messages_sent: int
    total_messages_received: int
    average_response_time: Optional[float]  # in seconds
    most_active_conversations: List[str]
    favorite_emojis: List[str]
    activity_by_hour: Dict[int, int] 