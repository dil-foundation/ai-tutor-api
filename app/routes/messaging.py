"""
Messaging System API Routes

This module provides comprehensive messaging functionality including:
- Conversation management (CRUD operations)
- Message handling with real-time delivery
- Participant management
- User status tracking
- WebSocket support for real-time communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import asyncio
import logging
from uuid import UUID, uuid4
import httpx
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
import jwt
from functools import wraps
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add detailed logging for WebSocket events
websocket_logger = logging.getLogger('websocket_events')
websocket_logger.setLevel(logging.INFO)

# Create Supabase client for messaging
try:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    logger.info(f"✅ [MESSAGING] Supabase client initialized for URL: {SUPABASE_URL}")
except Exception as e:
    logger.error(f"❌ [MESSAGING] Failed to initialize Supabase client: {str(e)}")
    raise

router = APIRouter()

# =====================================================
# PYDANTIC MODELS
# =====================================================

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    type: str = Field(default="direct", pattern="^(direct|group)$")
    participant_ids: List[str] = Field(..., min_items=1)

class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    type: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    is_archived: bool
    is_deleted: bool
    participants: List[Dict[str, Any]] = []
    unread_count: int = 0

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="text", pattern="^(text|image|file|system)$")
    reply_to_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: str
    reply_to_id: Optional[str]
    reply_to_content: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool
    metadata: Dict[str, Any]
    status: str = "sent"

class ParticipantAdd(BaseModel):
    user_id: str
    role: str = Field(default="participant", pattern="^(participant|admin|moderator)$")

class ParticipantResponse(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    user_name: str
    role: str
    joined_at: datetime
    left_at: Optional[datetime]
    is_muted: bool
    is_blocked: bool
    last_read_at: datetime

class UserStatus(BaseModel):
    status: str = Field(..., pattern="^(online|offline|away|busy)$")
    is_typing: bool = False
    typing_in_conversation: Optional[str] = None

class TypingStatus(BaseModel):
    conversation_id: str
    is_typing: bool

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=100)

class MessagesResponse(BaseModel):
    messages: List[MessageResponse]
    hasMore: bool
    total: int

# =====================================================
# AUTHENTICATION & AUTHORIZATION
# =====================================================

async def get_current_user(authorization: str = Depends(HTTPBearer())):
    """Extract and validate JWT token from Authorization header"""
    try:
        # Extract token from Bearer header
        token = authorization.credentials
        
        # Verify token with Supabase
        response = supabase_client.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.user
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

def require_participant(conversation_id: str):
    """Decorator to ensure user is a participant in the conversation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This will be implemented in each endpoint
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# =====================================================
# WEBSOCKET CONNECTION MANAGEMENT
# =====================================================

class ConnectionManager:
    """Manages WebSocket connections and real-time messaging"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_conversations: Dict[str, set] = {}  # user_id -> set of conversation_ids
        self.typing_users: Dict[str, Dict[str, datetime]] = {}  # conversation_id -> {user_id: timestamp}
        self.user_status: Dict[str, Dict[str, Any]] = {}  # user_id -> status info
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Handle new WebSocket connection"""
        # Connection is already accepted in websocket_endpoint
        self.active_connections[user_id] = websocket
        self.user_conversations[user_id] = set()
        
        # Update user status to online
        await self.update_user_status(user_id, "online")
        logger.info(f"User {user_id} connected")
        websocket_logger.info(f"🔌 [WEBSOCKET_CONNECT] User {user_id} established WebSocket connection")
        websocket_logger.info(f"📊 [WEBSOCKET_CONNECT] Total active connections: {len(self.active_connections)}")
        websocket_logger.info(f"👥 [WEBSOCKET_CONNECT] Active users: {list(self.active_connections.keys())}")
        websocket_logger.info(f"🔍 [WEBSOCKET_CONNECT] Connection manager state after connect:")
        websocket_logger.info(f"   - Active connections: {list(self.active_connections.keys())}")
        websocket_logger.info(f"   - User conversations: {dict(self.user_conversations)}")
    
    def disconnect(self, user_id: str):
        """Handle WebSocket disconnection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
        
        # Update user status to offline
        asyncio.create_task(self.update_user_status(user_id, "offline"))
        logger.info(f"User {user_id} disconnected")
        websocket_logger.info(f"🔌 [WEBSOCKET_DISCONNECT] User {user_id} disconnected from WebSocket")
        websocket_logger.info(f"📊 [WEBSOCKET_DISCONNECT] Remaining active connections: {len(self.active_connections)}")
        websocket_logger.info(f"👥 [WEBSOCKET_DISCONNECT] Remaining active users: {list(self.active_connections.keys())}")
    
    async def join_conversation(self, user_id: str, conversation_id: str):
        """Add user to conversation room"""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
        self.user_conversations[user_id].add(conversation_id)
        logger.info(f"✅ [JOIN] User {user_id} joined conversation {conversation_id}")
        logger.info(f"📊 [JOIN] Current user conversations: {dict(self.user_conversations)}")
        websocket_logger.info(f"🎯 [WEBSOCKET_JOIN] User {user_id} joined conversation {conversation_id}")
        websocket_logger.info(f"📊 [WEBSOCKET_JOIN] User {user_id} conversations: {list(self.user_conversations[user_id])}")
        websocket_logger.info(f"👥 [WEBSOCKET_JOIN] All user conversations: {dict(self.user_conversations)}")
    
    async def leave_conversation(self, user_id: str, conversation_id: str):
        """Remove user from conversation room"""
        if user_id in self.user_conversations:
            self.user_conversations[user_id].discard(conversation_id)
        logger.info(f"User {user_id} left conversation {conversation_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                # Ensure message is JSON serializable
                serializable_message = self._make_json_serializable(message)
                await self.active_connections[user_id].send_json(serializable_message)
                websocket_logger.info(f"📤 [WEBSOCKET_SEND] Message sent to user {user_id}")
                websocket_logger.info(f"📤 [WEBSOCKET_SEND] Message type: {message.get('type', 'unknown')}")
                websocket_logger.info(f"📤 [WEBSOCKET_SEND] Message content preview: {str(serializable_message)[:100]}...")
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {str(e)}")
                websocket_logger.error(f"❌ [WEBSOCKET_SEND] Failed to send message to {user_id}: {str(e)}")
                # Don't disconnect here to avoid dictionary modification during iteration
                # The connection will be cleaned up when the WebSocket actually disconnects
        else:
            websocket_logger.warning(f"⚠️ [WEBSOCKET_SEND] User {user_id} not connected, cannot send message")
    
    def _make_json_serializable(self, obj):
        """Convert datetime objects to ISO format strings for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    async def broadcast_to_conversation(self, message: dict, conversation_id: str, exclude_user: str = None):
        """Broadcast message to all users in a conversation"""
        if conversation_id not in self.typing_users:
            self.typing_users[conversation_id] = {}
        
        logger.info(f"🔍 [BROADCAST] Starting broadcast to conversation {conversation_id}")
        logger.info(f"🔍 [BROADCAST] Active connections: {list(self.active_connections.keys())}")
        logger.info(f"🔍 [BROADCAST] User conversations: {dict(self.user_conversations)}")
        logger.info(f"🔍 [BROADCAST] Excluding user: {exclude_user}")
        
        websocket_logger.info(f"📡 [WEBSOCKET_BROADCAST] Starting broadcast to conversation {conversation_id}")
        websocket_logger.info(f"📡 [WEBSOCKET_BROADCAST] Message type: {message.get('type', 'unknown')}")
        websocket_logger.info(f"📡 [WEBSOCKET_BROADCAST] Active connections: {list(self.active_connections.keys())}")
        websocket_logger.info(f"📡 [WEBSOCKET_BROADCAST] User conversations: {dict(self.user_conversations)}")
        websocket_logger.info(f"📡 [WEBSOCKET_BROADCAST] Excluding user: {exclude_user}")
        
        recipients = []
        # Create a copy of user_conversations to avoid dictionary modification during iteration
        user_conversations_copy = dict(self.user_conversations)
        
        for user_id, conversations in user_conversations_copy.items():
            logger.info(f"🔍 [BROADCAST] Checking user {user_id} with conversations {list(conversations)}")
            websocket_logger.info(f"🔍 [WEBSOCKET_BROADCAST] Checking user {user_id} with conversations {list(conversations)}")
            if conversation_id in conversations and user_id != exclude_user:
                logger.info(f"✅ [BROADCAST] User {user_id} is in conversation {conversation_id}")
                websocket_logger.info(f"✅ [WEBSOCKET_BROADCAST] User {user_id} is in conversation {conversation_id}")
                recipients.append(user_id)
                await self.send_personal_message(message, user_id)
            else:
                if conversation_id not in conversations:
                    logger.info(f"❌ [BROADCAST] User {user_id} is NOT in conversation {conversation_id}")
                    websocket_logger.warning(f"❌ [WEBSOCKET_BROADCAST] User {user_id} is NOT in conversation {conversation_id}")
                if user_id == exclude_user:
                    logger.info(f"❌ [BROADCAST] User {user_id} is excluded from broadcast")
                    websocket_logger.info(f"❌ [WEBSOCKET_BROADCAST] User {user_id} is excluded from broadcast")
        
        logger.info(f"📡 [BROADCAST] Sent message to {len(recipients)} users in conversation {conversation_id}: {recipients}")
        websocket_logger.info(f"📡 [WEBSOCKET_BROADCAST] Sent message to {len(recipients)} users in conversation {conversation_id}: {recipients}")
        if not recipients:
            websocket_logger.warning(f"⚠️ [WEBSOCKET_BROADCAST] No users received message in conversation {conversation_id}")
        return recipients
    
    async def update_user_status(self, user_id: str, status: str, is_typing: bool = False, conversation_id: str = None):
        """Update user status in memory and broadcast to relevant users"""
        try:
            # Store status in memory (database update is handled by the API endpoint)
            if user_id not in self.user_status:
                self.user_status[user_id] = {}
            
            self.user_status[user_id].update({
                'status': status,
                'is_typing': is_typing,
                'typing_in_conversation': conversation_id,
                'last_updated': datetime.now()
            })
            
            # Broadcast status change
            status_message = {
                'type': 'user_status_change',
                'user_id': user_id,
                'status': status,
                'is_typing': is_typing,
                'conversation_id': conversation_id
            }
            
            # Send to all users who might be interested
            # Create a copy of active_connections to avoid dictionary modification during iteration
            active_connections_copy = dict(self.active_connections)
            for other_user_id in active_connections_copy.keys():
                if other_user_id != user_id:
                    await self.send_personal_message(status_message, other_user_id)
                    
        except Exception as e:
            logger.error(f"Error updating user status: {str(e)}")

# Global connection manager
manager = ConnectionManager()

# =====================================================
# CONVERSATION MANAGEMENT ENDPOINTS
# =====================================================

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user = Depends(get_current_user)
):
    """Create a new conversation"""
    try:
        # Validate participants
        if len(conversation_data.participant_ids) < 1:
            raise HTTPException(status_code=400, detail="At least one participant required")
        
        # Ensure current user is included in participants
        if current_user.id not in conversation_data.participant_ids:
            conversation_data.participant_ids.append(current_user.id)
        
        # Create conversation
        conversation = {
            'title': conversation_data.title,
            'type': conversation_data.type,
            'created_by': current_user.id
        }
        
        result = supabase_client.table('conversations').insert(conversation).execute()
        conversation_id = result.data[0]['id']
        
        # Add participants
        participants_data = []
        for user_id in conversation_data.participant_ids:
            role = "admin" if user_id == current_user.id else "participant"
            participants_data.append({
                'conversation_id': conversation_id,
                'user_id': user_id,
                'role': role
            })
        
        supabase_client.table('conversation_participants').insert(participants_data).execute()
        
        # Return conversation with participants
        return await get_conversation_details(conversation_id, current_user)
        
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """Get user's conversations with pagination"""
    try:
        offset = (page - 1) * limit
        
        # Get conversations where user is a participant
        result = supabase_client.table('conversations')\
            .select('*')\
            .eq('is_deleted', False)\
            .order('last_message_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        conversations = []
        for conv in result.data:
            # Check if user is participant
            participant_check = supabase_client.table('conversation_participants')\
                .select('*')\
                .eq('conversation_id', conv['id'])\
                .eq('user_id', current_user.id)\
                .is_('left_at', 'null')\
                .execute()
            
            if participant_check.data:
                # Get participants
                participants = supabase_client.table('conversation_participants')\
                    .select('*, profiles(first_name, last_name)')\
                    .eq('conversation_id', conv['id'])\
                    .is_('left_at', 'null')\
                    .execute()
                
                # Get unread count
                unread_count = supabase_client.table('message_status')\
                    .select('*', count='exact')\
                    .eq('user_id', current_user.id)\
                    .eq('status', 'sent')\
                    .execute()
                
                conv['participants'] = participants.data
                conv['unread_count'] = unread_count.count or 0
                conversations.append(conv)
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user)
):
    """Get specific conversation details"""
    return await get_conversation_details(conversation_id, current_user)

async def get_conversation_details(conversation_id: str, current_user):
    """Helper function to get conversation details"""
    try:
        # Check if user is participant
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        if not participant_check.data:
            raise HTTPException(status_code=403, detail="Not a participant in this conversation")
        
        # Get conversation
        result = supabase_client.table('conversations')\
            .select('*')\
            .eq('id', conversation_id)\
            .eq('is_deleted', False)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation = result.data[0]
        
        # Get participants
        participants = supabase_client.table('conversation_participants')\
            .select('*, profiles(first_name, last_name)')\
            .eq('conversation_id', conversation_id)\
            .is_('left_at', 'null')\
            .execute()
        
        # Get unread count
        unread_count = supabase_client.table('message_status')\
            .select('*', count='exact')\
            .eq('user_id', current_user.id)\
            .eq('status', 'sent')\
            .execute()
        
        conversation['participants'] = participants.data
        conversation['unread_count'] = unread_count.count or 0
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get conversation details")

@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    title: Optional[str] = None,
    is_archived: Optional[bool] = None,
    current_user = Depends(get_current_user)
):
    """Update conversation (title, archive status)"""
    try:
        # Check if user is creator or admin
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        if not participant_check.data:
            raise HTTPException(status_code=403, detail="Not a participant in this conversation")
        
        # Check if user is creator or admin
        participant = participant_check.data[0]
        if participant['role'] not in ['admin', 'moderator']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Update conversation
        update_data = {}
        if title is not None:
            update_data['title'] = title
        if is_archived is not None:
            update_data['is_archived'] = is_archived
        
        if update_data:
            supabase_client.table('conversations')\
                .update(update_data)\
                .eq('id', conversation_id)\
                .execute()
        
        return await get_conversation_details(conversation_id, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update conversation")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user)
):
    """Delete conversation (soft delete)"""
    try:
        # Check if user is creator
        conversation = supabase_client.table('conversations')\
            .select('*')\
            .eq('id', conversation_id)\
            .eq('created_by', current_user.id)\
            .execute()
        
        if not conversation.data:
            raise HTTPException(status_code=403, detail="Not the creator of this conversation")
        
        # Soft delete
        supabase_client.table('conversations')\
            .update({'is_deleted': True})\
            .eq('id', conversation_id)\
            .execute()
        
        return {"message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

# =====================================================
# MESSAGE MANAGEMENT ENDPOINTS
# =====================================================

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user = Depends(get_current_user)
):
    """Send a message to a conversation"""
    try:
        # Check if user is participant
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        if not participant_check.data:
            raise HTTPException(status_code=403, detail="Not a participant in this conversation")
        
        # Create message
        message = {
            'conversation_id': conversation_id,
            'sender_id': current_user.id,
            'content': message_data.content,
            'message_type': message_data.message_type,
            'reply_to_id': message_data.reply_to_id,
            'metadata': message_data.metadata or {}
        }
        
        result = supabase_client.table('messages').insert(message).execute()
        message_id = result.data[0]['id']
        
        # Get full message with sender info
        full_message = await get_message_details(message_id, current_user)
        
        # Update conversation's last_message_at
        supabase_client.table('conversations')\
            .update({'last_message_at': datetime.now().isoformat()})\
            .eq('id', conversation_id)\
            .execute()
        
        # Create message status entries for all participants
        participants = supabase_client.table('conversation_participants')\
            .select('user_id')\
            .eq('conversation_id', conversation_id)\
            .is_('left_at', 'null')\
            .execute()
        
        if participants.data:
            status_entries = []
            for participant in participants.data:
                if participant['user_id'] != current_user.id:  # Don't create status for sender
                    status_entries.append({
                        'message_id': message_id,
                        'user_id': participant['user_id'],
                        'status': 'sent'
                    })
            
            if status_entries:
                logger.info(f"📝 [SEND_MESSAGE] Creating {len(status_entries)} message status entries for message {message_id}")
                try:
                    # Check for existing entries and only insert new ones
                    for status_entry in status_entries:
                        # Check if entry already exists
                        existing = supabase_client.table('message_status')\
                            .select('*')\
                            .eq('message_id', status_entry['message_id'])\
                            .eq('user_id', status_entry['user_id'])\
                            .execute()
                        
                        if not existing.data:
                            # Entry doesn't exist, insert it
                            supabase_client.table('message_status').insert(status_entry).execute()
                            logger.info(f"✅ [SEND_MESSAGE] Created status entry for user {status_entry['user_id']}")
                        else:
                            logger.info(f"ℹ️ [SEND_MESSAGE] Status entry already exists for user {status_entry['user_id']}")
                    
                    logger.info(f"✅ [SEND_MESSAGE] Successfully processed message status entries")
                except Exception as status_error:
                    logger.error(f"❌ [SEND_MESSAGE] Error creating message status entries: {str(status_error)}")
                    # Don't fail the entire request if status creation fails
        
        # Broadcast to conversation participants via WebSocket
        broadcast_message = {
            'type': 'new_message',
            'message': full_message.dict(),
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat()
        }
        
        websocket_logger.info(f"📡 [SEND_MESSAGE_WEBSOCKET] Preparing to broadcast message {message_id} to conversation {conversation_id}")
        websocket_logger.info(f"📡 [SEND_MESSAGE_WEBSOCKET] Broadcast message content: {broadcast_message}")
        
        try:
            recipients = await manager.broadcast_to_conversation(broadcast_message, conversation_id, current_user.id)
            logger.info(f"📡 [SEND_MESSAGE] Broadcasted message {message_id} to conversation {conversation_id}")
            websocket_logger.info(f"📡 [SEND_MESSAGE_WEBSOCKET] Broadcasted message {message_id} to conversation {conversation_id}")
            websocket_logger.info(f"📡 [SEND_MESSAGE_WEBSOCKET] Recipients: {recipients}")
            
            # If no users are connected via WebSocket, log this for debugging
            if not recipients:
                logger.warning(f"⚠️ [SEND_MESSAGE] No users connected via WebSocket for conversation {conversation_id}")
                logger.info(f"📋 [SEND_MESSAGE] Message {message_id} will be available when users connect and fetch messages")
                websocket_logger.warning(f"⚠️ [SEND_MESSAGE_WEBSOCKET] No users connected via WebSocket for conversation {conversation_id}")
                websocket_logger.info(f"📋 [SEND_MESSAGE_WEBSOCKET] Message {message_id} will be available when users connect and fetch messages")
        except Exception as broadcast_error:
            logger.error(f"❌ [SEND_MESSAGE] Failed to broadcast message: {str(broadcast_error)}")
            websocket_logger.error(f"❌ [SEND_MESSAGE_WEBSOCKET] Failed to broadcast message: {str(broadcast_error)}")
            # Don't fail the request if broadcasting fails
        
        return full_message
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send message")

@router.get("/conversations/{conversation_id}/messages", response_model=MessagesResponse)
async def get_messages(
    conversation_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """Get conversation messages with pagination"""
    try:
        logger.info(f"🔍 [MESSAGES] Getting messages for conversation: {conversation_id}, user: {current_user.id}, page: {page}, limit: {limit}")
        
        # Check if user is participant
        logger.info(f"🔍 [MESSAGES] Checking participant status...")
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        logger.info(f"🔍 [MESSAGES] Participant check result: {len(participant_check.data) if participant_check.data else 0} records")
        
        if not participant_check.data:
            logger.warning(f"⚠️ [MESSAGES] User {current_user.id} is not a participant in conversation {conversation_id}")
            raise HTTPException(status_code=403, detail="Not a participant in this conversation")
        
        # Get total count first
        total_count_result = supabase_client.table('messages')\
            .select('*', count='exact')\
            .eq('conversation_id', conversation_id)\
            .eq('is_deleted', False)\
            .execute()
        
        total = total_count_result.count or 0
        logger.info(f"🔍 [MESSAGES] Total messages in conversation: {total}")
        
        offset = (page - 1) * limit
        logger.info(f"🔍 [MESSAGES] Fetching messages with offset: {offset}")
        
        # Get messages
        result = supabase_client.table('messages')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('is_deleted', False)\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        logger.info(f"🔍 [MESSAGES] Found {len(result.data) if result.data else 0} messages")
        
        messages = []
        for msg in result.data:
            logger.info(f"🔍 [MESSAGES] Processing message: {msg.get('id', 'unknown')}")
            try:
                message_details = await get_message_details(msg['id'], current_user)
                messages.append(message_details)
            except Exception as msg_error:
                logger.error(f"❌ [MESSAGES] Error processing message {msg.get('id', 'unknown')}: {str(msg_error)}")
                # Continue with other messages instead of failing completely
                continue
        
        # Calculate if there are more messages
        has_more = (offset + limit) < total
        
        logger.info(f"✅ [MESSAGES] Successfully returned {len(messages)} messages, hasMore: {has_more}, total: {total}")
        
        return MessagesResponse(
            messages=messages,
            hasMore=has_more,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [MESSAGES] Error getting messages: {str(e)}")
        logger.error(f"❌ [MESSAGES] Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [MESSAGES] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to get messages")

async def get_message_details(message_id: str, current_user):
    """Helper function to get message details with sender info"""
    try:
        logger.info(f"🔍 [MESSAGE_DETAILS] Getting details for message: {message_id}")
        
        result = supabase_client.table('messages')\
            .select('*')\
            .eq('id', message_id)\
            .execute()
        
        if not result.data:
            logger.warning(f"⚠️ [MESSAGE_DETAILS] Message not found: {message_id}")
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = result.data[0]
        logger.info(f"🔍 [MESSAGE_DETAILS] Found message: {message.get('id', 'unknown')}, sender: {message.get('sender_id', 'unknown')}")
        
        # Ensure all required fields are present with defaults
        message_data = {
            'id': message.get('id'),
            'conversation_id': message.get('conversation_id'),
            'sender_id': message.get('sender_id'),
            'content': message.get('content', ''),
            'message_type': message.get('message_type', 'text'),
            'reply_to_id': message.get('reply_to_id'),
            'reply_to_content': None,
            'created_at': message.get('created_at'),
            'updated_at': message.get('updated_at'),
            'is_edited': message.get('is_edited', False),
            'is_deleted': message.get('is_deleted', False),
            'metadata': message.get('metadata', {}),
            'status': 'sent',
            'sender_name': 'Unknown User'
        }
        
        # Get sender info
        if message_data['sender_id']:
            try:
                sender = supabase_client.table('profiles')\
                    .select('first_name, last_name')\
                    .eq('id', message_data['sender_id'])\
                    .execute()
                
                if sender.data:
                    first_name = sender.data[0].get('first_name', '')
                    last_name = sender.data[0].get('last_name', '')
                    message_data['sender_name'] = f"{first_name} {last_name}".strip() or "Unknown User"
                    logger.info(f"🔍 [MESSAGE_DETAILS] Sender name: {message_data['sender_name']}")
                else:
                    logger.warning(f"⚠️ [MESSAGE_DETAILS] Sender profile not found for: {message_data['sender_id']}")
            except Exception as sender_error:
                logger.error(f"❌ [MESSAGE_DETAILS] Error getting sender info: {str(sender_error)}")
                message_data['sender_name'] = "Unknown User"
        
        # Get reply message if exists
        if message_data['reply_to_id']:
            try:
                reply_msg = supabase_client.table('messages')\
                    .select('content')\
                    .eq('id', message_data['reply_to_id'])\
                    .execute()
                if reply_msg.data:
                    message_data['reply_to_content'] = reply_msg.data[0].get('content', '')
                    logger.info(f"🔍 [MESSAGE_DETAILS] Reply content found for: {message_data['reply_to_id']}")
            except Exception as reply_error:
                logger.error(f"❌ [MESSAGE_DETAILS] Error getting reply content: {str(reply_error)}")
        
        # Get message status for current user
        try:
            status = supabase_client.table('message_status')\
                .select('status')\
                .eq('message_id', message_id)\
                .eq('user_id', current_user.id)\
                .execute()
            
            if status.data:
                message_data['status'] = status.data[0].get('status', 'sent')
                logger.info(f"🔍 [MESSAGE_DETAILS] Message status: {message_data['status']}")
            else:
                logger.info(f"🔍 [MESSAGE_DETAILS] No status found, defaulting to 'sent'")
        except Exception as status_error:
            logger.error(f"❌ [MESSAGE_DETAILS] Error getting message status: {str(status_error)}")
            message_data['status'] = 'sent'
        
        logger.info(f"✅ [MESSAGE_DETAILS] Successfully processed message: {message_id}")
        return MessageResponse(**message_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [MESSAGE_DETAILS] Error getting message details: {str(e)}")
        logger.error(f"❌ [MESSAGE_DETAILS] Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [MESSAGE_DETAILS] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to get message details")

@router.put("/messages/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: str,
    content: str = Form(..., min_length=1, max_length=5000),
    current_user = Depends(get_current_user)
):
    """Edit a message"""
    try:
        # Get message and check ownership
        result = supabase_client.table('messages')\
            .select('*')\
            .eq('id', message_id)\
            .eq('sender_id', current_user.id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Message not found or not owned by you")
        
        message = result.data[0]
        
        # Update message
        supabase_client.table('messages')\
            .update({
                'content': content,
                'is_edited': True,
                'updated_at': datetime.now().isoformat()
            })\
            .eq('id', message_id)\
            .execute()
        
        # Get updated message
        return await get_message_details(message_id, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to edit message")

@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a message (soft delete)"""
    try:
        # Get message and check ownership
        result = supabase_client.table('messages')\
            .select('*')\
            .eq('id', message_id)\
            .eq('sender_id', current_user.id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Message not found or not owned by you")
        
        # Soft delete
        supabase_client.table('messages')\
            .update({'is_deleted': True})\
            .eq('id', message_id)\
            .execute()
        
        return {"message": "Message deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete message")

@router.post("/messages/{message_id}/read")
async def mark_message_read(
    message_id: str,
    current_user = Depends(get_current_user)
):
    """Mark message as read"""
    try:
        # Update message status
        supabase_client.table('message_status')\
            .update({'status': 'read'})\
            .eq('message_id', message_id)\
            .eq('user_id', current_user.id)\
            .execute()
        
        return {"message": "Message marked as read"}
        
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark message as read")

# =====================================================
# PARTICIPANT MANAGEMENT ENDPOINTS
# =====================================================

@router.post("/conversations/{conversation_id}/participants", response_model=ParticipantResponse)
async def add_participant(
    conversation_id: str,
    participant_data: ParticipantAdd,
    current_user = Depends(get_current_user)
):
    """Add participant to conversation"""
    try:
        # Check if user is admin/moderator
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        if not participant_check.data or participant_check.data[0]['role'] not in ['admin', 'moderator']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Add participant
        participant = {
            'conversation_id': conversation_id,
            'user_id': participant_data.user_id,
            'role': participant_data.role
        }
        
        result = supabase_client.table('conversation_participants').insert(participant).execute()
        
        # Get participant details
        participant_details = supabase_client.table('conversation_participants')\
            .select('*, profiles(first_name, last_name)')\
            .eq('id', result.data[0]['id'])\
            .execute()
        
        return participant_details.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding participant: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add participant")

@router.delete("/conversations/{conversation_id}/participants/{user_id}")
async def remove_participant(
    conversation_id: str,
    user_id: str,
    current_user = Depends(get_current_user)
):
    """Remove participant from conversation"""
    try:
        # Check if user is admin or removing themselves
        if user_id != current_user.id:
            participant_check = supabase_client.table('conversation_participants')\
                .select('*')\
                .eq('conversation_id', conversation_id)\
                .eq('user_id', current_user.id)\
                .is_('left_at', 'null')\
                .execute()
            
            if not participant_check.data or participant_check.data[0]['role'] not in ['admin', 'moderator']:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Mark participant as left
        supabase_client.table('conversation_participants')\
            .update({'left_at': datetime.now().isoformat()})\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', user_id)\
            .execute()
        
        return {"message": "Participant removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing participant: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to remove participant")

@router.put("/conversations/{conversation_id}/participants/{user_id}")
async def update_participant(
    conversation_id: str,
    user_id: str,
    role: Optional[str] = Form(None),
    is_muted: Optional[bool] = Form(None),
    current_user = Depends(get_current_user)
):
    """Update participant role/mute status"""
    try:
        # Check if user is admin
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        if not participant_check.data or participant_check.data[0]['role'] != 'admin':
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Update participant
        update_data = {}
        if role is not None:
            update_data['role'] = role
        if is_muted is not None:
            update_data['is_muted'] = is_muted
        
        if update_data:
            supabase_client.table('conversation_participants')\
                .update(update_data)\
                .eq('conversation_id', conversation_id)\
                .eq('user_id', user_id)\
                .execute()
        
        return {"message": "Participant updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating participant: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update participant")

# =====================================================
# USER STATUS ENDPOINTS
# =====================================================

@router.get("/users/status")
async def get_users_status(
    user_ids: List[str] = Query(...),
    current_user = Depends(get_current_user)
):
    """Get online status of users"""
    try:
        logger.info(f"🔍 [USER_STATUS] Getting status for users: {user_ids}")
        
        result = supabase_client.table('user_status')\
            .select('*')\
            .in_('user_id', user_ids)\
            .execute()
        
        logger.info(f"✅ [USER_STATUS] Found {len(result.data) if result.data else 0} status records")
        return result.data
        
    except Exception as e:
        logger.error(f"❌ [USER_STATUS] Error getting users status: {str(e)}")
        logger.error(f"❌ [USER_STATUS] Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [USER_STATUS] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to get users status")

@router.put("/users/status")
async def update_user_status(
    status_data: UserStatus,
    current_user = Depends(get_current_user)
):
    """Update own status"""
    try:
        # First, check if a status record already exists for this user
        existing_status = supabase_client.table('user_status')\
            .select('id')\
            .eq('user_id', current_user.id)\
            .execute()
        
        status_data_to_upsert = {
            'user_id': current_user.id,
            'status': status_data.status,
            'last_seen_at': datetime.now().isoformat(),
            'is_typing': status_data.is_typing,
            'typing_in_conversation': status_data.typing_in_conversation
        }
        
        # If record exists, include the id for update; otherwise, let Supabase generate a new id
        if existing_status.data:
            status_data_to_upsert['id'] = existing_status.data[0]['id']
            logger.info(f"📝 [USER_STATUS] Updating existing status record for user {current_user.id}")
        else:
            logger.info(f"📝 [USER_STATUS] Creating new status record for user {current_user.id}")
        
        # Update status in database
        supabase_client.table('user_status')\
            .upsert(status_data_to_upsert)\
            .execute()
        
        # Update in connection manager
        await manager.update_user_status(
            current_user.id, 
            status_data.status, 
            status_data.is_typing, 
            status_data.typing_in_conversation
        )
        
        logger.info(f"✅ [USER_STATUS] Successfully updated status for user {current_user.id}: {status_data.status}")
        return {"message": "Status updated successfully"}
        
    except Exception as e:
        logger.error(f"❌ [USER_STATUS] Error updating user status: {str(e)}")
        logger.error(f"❌ [USER_STATUS] Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [USER_STATUS] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to update user status")

# =====================================================
# WEBSOCKET ENDPOINT
# =====================================================

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time messaging"""
    user_id = None
    connection_accepted = False
    
    try:
        logger.info(f"🔌 [WEBSOCKET] New connection attempt with token: {token[:20]}...")
        websocket_logger.info(f"🔌 [WEBSOCKET_ENDPOINT] New connection attempt with token: {token[:20]}...")
        
        # Authenticate user BEFORE accepting connection
        try:
            response = supabase_client.auth.get_user(token)
            if not response.user:
                logger.warning(f"⚠️ [WEBSOCKET] Invalid token provided")
                websocket_logger.warning(f"⚠️ [WEBSOCKET_ENDPOINT] Invalid token provided")
                # Don't accept connection if token is invalid
                return
            user_id = response.user.id
            logger.info(f"🔌 [WEBSOCKET] User authenticated: {user_id}")
            websocket_logger.info(f"🔌 [WEBSOCKET_ENDPOINT] User authenticated: {user_id}")
        except Exception as e:
            logger.error(f"❌ [WEBSOCKET] Authentication error: {str(e)}")
            websocket_logger.error(f"❌ [WEBSOCKET_ENDPOINT] Authentication error: {str(e)}")
            # Don't accept connection if authentication fails
            return
        
        # Accept the connection only after successful authentication
        await websocket.accept()
        connection_accepted = True
        logger.info(f"🔌 [WEBSOCKET] Connection accepted for user {user_id}")
        websocket_logger.info(f"🔌 [WEBSOCKET_ENDPOINT] Connection accepted for user {user_id}")
        
        # Connect user to manager
        await manager.connect(websocket, user_id)
        logger.info(f"🔌 [WEBSOCKET] User {user_id} connected to manager")
        websocket_logger.info(f"🔌 [WEBSOCKET_ENDPOINT] User {user_id} connected to manager")
        
        # Send connection confirmation
        await websocket.send_json({
            'type': 'connection_established',
            'user_id': user_id,
            'message': 'WebSocket connection established'
        })
        websocket_logger.info(f"📤 [WEBSOCKET_ENDPOINT] Sent connection confirmation to user {user_id}")
        
        # Automatically join user to all their active conversations
        try:
            logger.info(f"🔍 [WEBSOCKET] Auto-joining user {user_id} to their conversations")
            websocket_logger.info(f"🔍 [WEBSOCKET_ENDPOINT] Auto-joining user {user_id} to their conversations")
            conversations = supabase_client.table('conversation_participants')\
                .select('conversation_id')\
                .eq('user_id', user_id)\
                .is_('left_at', 'null')\
                .execute()
            
            websocket_logger.info(f"🔍 [WEBSOCKET_ENDPOINT] Found {len(conversations.data)} conversations for user {user_id}")
            
            if conversations.data:
                for conv in conversations.data:
                    conversation_id = conv['conversation_id']
                    await manager.join_conversation(user_id, conversation_id)
                    logger.info(f"✅ [WEBSOCKET] Auto-joined user {user_id} to conversation {conversation_id}")
                    websocket_logger.info(f"✅ [WEBSOCKET_ENDPOINT] Auto-joined user {user_id} to conversation {conversation_id}")
                
                await websocket.send_json({
                    'type': 'auto_joined_conversations',
                    'conversation_ids': [conv['conversation_id'] for conv in conversations.data],
                    'message': f'Auto-joined {len(conversations.data)} conversations'
                })
                websocket_logger.info(f"📤 [WEBSOCKET_ENDPOINT] Sent auto-join confirmation to user {user_id}")
            else:
                logger.info(f"ℹ️ [WEBSOCKET] User {user_id} has no active conversations to join")
                websocket_logger.info(f"ℹ️ [WEBSOCKET_ENDPOINT] User {user_id} has no active conversations to join")
        except Exception as e:
            logger.error(f"❌ [WEBSOCKET] Error auto-joining conversations: {str(e)}")
            websocket_logger.error(f"❌ [WEBSOCKET_ENDPOINT] Error auto-joining conversations: {str(e)}")
            # Don't fail the connection if auto-join fails
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"📨 [WEBSOCKET] Received message from {user_id}: {data.get('type', 'unknown')}")
                websocket_logger.info(f"📨 [WEBSOCKET_ENDPOINT] Received message from {user_id}: {data.get('type', 'unknown')}")
                websocket_logger.info(f"📨 [WEBSOCKET_ENDPOINT] Message content: {data}")
                await handle_websocket_message(websocket, user_id, data)
            except WebSocketDisconnect:
                logger.info(f"🔌 [WEBSOCKET] User {user_id} disconnected")
                websocket_logger.info(f"🔌 [WEBSOCKET_ENDPOINT] User {user_id} disconnected")
                break
            except Exception as e:
                logger.error(f"❌ [WEBSOCKET] Message handling error: {str(e)}")
                if connection_accepted:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Invalid message format',
                        'error': str(e)
                    })
                
    except WebSocketDisconnect:
        logger.info(f"🔌 [WEBSOCKET] WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"❌ [WEBSOCKET] Unexpected error: {str(e)}")
    finally:
        if user_id:
            manager.disconnect(user_id)
            logger.info(f"🔌 [WEBSOCKET] User {user_id} cleaned up from manager")

async def handle_websocket_message(websocket: WebSocket, user_id: str, data: dict):
    """Handle incoming WebSocket messages"""
    message_type = data.get('type')
    
    try:
        logger.info(f"🔍 [WEBSOCKET_HANDLER] Processing {message_type} for user {user_id}")
        websocket_logger.info(f"🔍 [WEBSOCKET_HANDLER] Processing {message_type} for user {user_id}")
        websocket_logger.info(f"🔍 [WEBSOCKET_HANDLER] Full message data: {data}")
        
        if message_type == 'join_conversation':
            conversation_id = data.get('conversation_id')
            websocket_logger.info(f"🔍 [WEBSOCKET_HANDLER] Join request for conversation: {conversation_id}")
            
            if conversation_id:
                # Verify user is participant in conversation
                try:
                    participant_check = supabase_client.table('conversation_participants')\
                        .select('*')\
                        .eq('conversation_id', conversation_id)\
                        .eq('user_id', user_id)\
                        .is_('left_at', 'null')\
                        .execute()
                    
                    websocket_logger.info(f"🔍 [WEBSOCKET_HANDLER] Participant check result: {len(participant_check.data) if participant_check.data else 0} records")
                    
                    if participant_check.data:
                        await manager.join_conversation(user_id, conversation_id)
                        await websocket.send_json({
                            'type': 'joined_conversation',
                            'conversation_id': conversation_id,
                            'user_id': user_id
                        })
                        logger.info(f"✅ [WEBSOCKET_HANDLER] User {user_id} joined conversation {conversation_id}")
                        websocket_logger.info(f"✅ [WEBSOCKET_HANDLER] User {user_id} joined conversation {conversation_id}")
                    else:
                        await websocket.send_json({
                            'type': 'error',
                            'message': 'Not a participant in this conversation'
                        })
                        logger.warning(f"⚠️ [WEBSOCKET_HANDLER] User {user_id} tried to join conversation {conversation_id} without permission")
                        websocket_logger.warning(f"⚠️ [WEBSOCKET_HANDLER] User {user_id} tried to join conversation {conversation_id} without permission")
                except Exception as e:
                    logger.error(f"❌ [WEBSOCKET_HANDLER] Error checking participant status: {str(e)}")
                    websocket_logger.error(f"❌ [WEBSOCKET_HANDLER] Error checking participant status: {str(e)}")
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Error checking participant status',
                        'error': str(e)
                    })
            else:
                logger.warning(f"⚠️ [WEBSOCKET_HANDLER] No conversation_id provided in join request")
                websocket_logger.warning(f"⚠️ [WEBSOCKET_HANDLER] No conversation_id provided in join request")
                await websocket.send_json({
                    'type': 'error',
                    'message': 'No conversation_id provided'
                })
        
        elif message_type == 'leave_conversation':
            conversation_id = data.get('conversation_id')
            if conversation_id:
                await manager.leave_conversation(user_id, conversation_id)
                await websocket.send_json({
                    'type': 'left_conversation',
                    'conversation_id': conversation_id,
                    'user_id': user_id
                })
                logger.info(f"✅ [WEBSOCKET_HANDLER] User {user_id} left conversation {conversation_id}")
        
        elif message_type == 'typing_start':
            conversation_id = data.get('conversation_id')
            if conversation_id:
                await manager.update_user_status(user_id, 'online', True, conversation_id)
                await manager.broadcast_to_conversation({
                    'type': 'typing_start',
                    'user_id': user_id,
                    'conversation_id': conversation_id,
                    'timestamp': datetime.now().isoformat()
                }, conversation_id, user_id)
                logger.info(f"⌨️ [WEBSOCKET_HANDLER] User {user_id} started typing in {conversation_id}")
        
        elif message_type == 'typing_stop':
            conversation_id = data.get('conversation_id')
            if conversation_id:
                await manager.update_user_status(user_id, 'online', False, None)
                await manager.broadcast_to_conversation({
                    'type': 'typing_stop',
                    'user_id': user_id,
                    'conversation_id': conversation_id,
                    'timestamp': datetime.now().isoformat()
                }, conversation_id, user_id)
                logger.info(f"⌨️ [WEBSOCKET_HANDLER] User {user_id} stopped typing in {conversation_id}")
        
        elif message_type == 'message_read':
            message_id = data.get('message_id')
            conversation_id = data.get('conversation_id')
            if message_id and conversation_id:
                try:
                    # Update message status
                    logger.info(f"📝 [WEBSOCKET_HANDLER] Marking message {message_id} as read by {user_id}")
                    supabase_client.table('message_status')\
                        .upsert({
                            'message_id': message_id,
                            'user_id': user_id,
                            'status': 'read'
                        })\
                        .execute()
                    
                    # Broadcast read receipt
                    await manager.broadcast_to_conversation({
                        'type': 'message_read',
                        'message_id': message_id,
                        'user_id': user_id,
                        'conversation_id': conversation_id,
                        'timestamp': datetime.now().isoformat()
                    }, conversation_id, user_id)
                    logger.info(f"✅ [WEBSOCKET_HANDLER] Message {message_id} marked as read by {user_id}")
                except Exception as e:
                    logger.error(f"❌ [WEBSOCKET_HANDLER] Error marking message as read: {str(e)}")
                    logger.error(f"❌ [WEBSOCKET_HANDLER] Error type: {type(e).__name__}")
                    import traceback
                    logger.error(f"❌ [WEBSOCKET_HANDLER] Traceback: {traceback.format_exc()}")
        
        elif message_type == 'ping':
            # Handle ping for connection health check
            await websocket.send_json({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            })
            logger.debug(f"🏓 [WEBSOCKET_HANDLER] Ping from user {user_id}")
        
        else:
            await websocket.send_json({
                'type': 'error',
                'message': f'Unknown message type: {message_type}',
                'supported_types': ['join_conversation', 'leave_conversation', 'typing_start', 'typing_stop', 'message_read', 'ping']
            })
            logger.warning(f"⚠️ [WEBSOCKET_HANDLER] Unknown message type: {message_type} from user {user_id}")
            
    except Exception as e:
        logger.error(f"❌ [WEBSOCKET_HANDLER] Error handling WebSocket message: {str(e)}")
        logger.error(f"❌ [WEBSOCKET_HANDLER] Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ [WEBSOCKET_HANDLER] Traceback: {traceback.format_exc()}")
        await websocket.send_json({
            'type': 'error',
            'message': 'Internal server error',
            'error': str(e)
        })

# =====================================================
# DEBUG ENDPOINTS
# =====================================================

@router.get("/debug/conversations/{conversation_id}")
async def debug_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user)
):
    """Debug endpoint to check conversation and messages"""
    try:
        logger.info(f"🔍 [DEBUG] Checking conversation: {conversation_id}")
        
        # Check if conversation exists
        conv_result = supabase_client.table('conversations')\
            .select('*')\
            .eq('id', conversation_id)\
            .execute()
        
        if not conv_result.data:
            return {"error": "Conversation not found", "conversation_id": conversation_id}
        
        conversation = conv_result.data[0]
        logger.info(f"🔍 [DEBUG] Conversation found: {conversation}")
        
        # Check messages count
        messages_count = supabase_client.table('messages')\
            .select('*', count='exact')\
            .eq('conversation_id', conversation_id)\
            .eq('is_deleted', False)\
            .execute()
        
        # Check participants
        participants = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .is_('left_at', 'null')\
            .execute()
        
        return {
            "conversation": conversation,
            "messages_count": messages_count.count or 0,
            "participants_count": len(participants.data) if participants.data else 0,
            "current_user_id": current_user.id,
            "is_participant": any(p['user_id'] == current_user.id for p in participants.data) if participants.data else False
        }
        
    except Exception as e:
        logger.error(f"❌ [DEBUG] Error: {str(e)}")
        return {"error": str(e)}

@router.get("/debug/websocket/connections")
async def debug_websocket_connections():
    """Debug endpoint to check WebSocket connections"""
    try:
        active_connections = len(manager.active_connections)
        user_conversations = {}
        
        for user_id, conversations in manager.user_conversations.items():
            user_conversations[user_id] = list(conversations)
        
        # Get user details for connected users
        connected_user_details = []
        for user_id in manager.active_connections.keys():
            try:
                user_profile = supabase_client.table('profiles')\
                    .select('first_name, last_name')\
                    .eq('id', user_id)\
                    .execute()
                
                if user_profile.data:
                    name = f"{user_profile.data[0].get('first_name', '')} {user_profile.data[0].get('last_name', '')}".strip()
                    connected_user_details.append({
                        'user_id': user_id,
                        'name': name or 'Unknown',
                        'conversations': list(manager.user_conversations.get(user_id, set()))
                    })
            except Exception as e:
                logger.error(f"❌ [DEBUG] Error getting user details for {user_id}: {str(e)}")
                connected_user_details.append({
                    'user_id': user_id,
                    'name': 'Error getting name',
                    'conversations': list(manager.user_conversations.get(user_id, set()))
                })
        
        return {
            "active_connections": active_connections,
            "connected_users": list(manager.active_connections.keys()),
            "connected_user_details": connected_user_details,
            "user_conversations": user_conversations,
            "typing_users": manager.typing_users
        }
        
    except Exception as e:
        logger.error(f"❌ [DEBUG] WebSocket debug error: {str(e)}")
        return {"error": str(e)}

# =====================================================
# FILE UPLOAD ENDPOINTS
# =====================================================

@router.post("/conversations/{conversation_id}/upload")
async def upload_file(
    conversation_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload file to conversation"""
    try:
        # Check if user is participant
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        if not participant_check.data:
            raise HTTPException(status_code=403, detail="Not a participant in this conversation")
        
        # Validate file type and size
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain']
        max_size = 10 * 1024 * 1024  # 10MB
        
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="File type not allowed")
        
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Upload to Supabase Storage (implementation depends on your storage setup)
        # For now, we'll store file info in message metadata
        
        # Create message with file metadata
        message = {
            'conversation_id': conversation_id,
            'sender_id': current_user.id,
            'content': f"Uploaded file: {file.filename}",
            'message_type': 'file',
            'metadata': {
                'filename': file.filename,
                'content_type': file.content_type,
                'size': len(file_content),
                'uploaded_at': datetime.now().isoformat()
            }
        }
        
        result = supabase_client.table('messages').insert(message).execute()
        message_id = result.data[0]['id']
        
        # Get full message
        full_message = await get_message_details(message_id, current_user)
        
        # Broadcast to conversation participants
        broadcast_message = {
            'type': 'new_message',
            'message': full_message.dict()
        }
        await manager.broadcast_to_conversation(broadcast_message, conversation_id, current_user.id)
        
        return full_message
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file") 
