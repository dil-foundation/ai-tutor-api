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
from fastapi.responses import JSONResponse, Response
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import asyncio
import logging
import traceback
from uuid import UUID, uuid4
import httpx
from app.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
import jwt
from functools import wraps
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Supabase client for messaging
try:
    supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
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

class ConversationsResponse(BaseModel):
    conversations: List[ConversationResponse]
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
        
        # Update user status to online in database
        await self.update_user_status_in_database(user_id, "online")
        
        # Update user status in memory and broadcast
        await self.update_user_status(user_id, "online")
    
    def disconnect(self, user_id: str):
        """Handle WebSocket disconnection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
        
        # Update user status to offline in database and memory
        asyncio.create_task(self.update_user_status_in_database(user_id, "offline"))
        asyncio.create_task(self.update_user_status(user_id, "offline"))
    
    async def join_conversation(self, user_id: str, conversation_id: str):
        """Add user to conversation room"""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
        self.user_conversations[user_id].add(conversation_id)
    
    async def leave_conversation(self, user_id: str, conversation_id: str):
        """Remove user from conversation room"""
        if user_id in self.user_conversations:
            self.user_conversations[user_id].discard(conversation_id)
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                # Ensure message is JSON serializable
                serializable_message = self._make_json_serializable(message)
                await self.active_connections[user_id].send_json(serializable_message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {str(e)}")
                # Don't disconnect here to avoid dictionary modification during iteration
                # The connection will be cleaned up when the WebSocket actually disconnects
    
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
        
        recipients = []
        # Create a copy of user_conversations to avoid dictionary modification during iteration
        user_conversations_copy = dict(self.user_conversations)
        
        for user_id, conversations in user_conversations_copy.items():
            if conversation_id in conversations and user_id != exclude_user:
                recipients.append(user_id)
                await self.send_personal_message(message, user_id)
        
        return recipients
    
    async def update_user_status_in_database(self, user_id: str, status: str, is_typing: bool = False, conversation_id: str = None):
        """Update user status in the database"""
        try:
            # First, check if a status record already exists for this user
            existing_status = supabase_client.table('user_status')\
                .select('id')\
                .eq('user_id', user_id)\
                .execute()
            
            status_data_to_upsert = {
                'user_id': user_id,
                'status': status,
                'last_seen_at': datetime.now().isoformat(),
                'is_typing': is_typing,
                'typing_in_conversation': conversation_id
            }
            
            # If record exists, include the id for update; otherwise, let Supabase generate a new id
            if existing_status.data:
                status_data_to_upsert['id'] = existing_status.data[0]['id']
            
            # Update status in database
            supabase_client.table('user_status')\
                .upsert(status_data_to_upsert)\
                .execute()
            
        except Exception as e:
            logger.error(f"Error updating user status in database: {str(e)}")

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
        
        # Get the complete conversation details for broadcasting
        conversation_details = await get_conversation_details(conversation_id, current_user)

        # Broadcast new_conversation event to all participants except the creator
        try:
            new_conversation_event = {
                "type": "new_conversation",
                "conversation": conversation_details
            }
            
            # Send to all participants except the creator
            for user_id in conversation_data.participant_ids:
                if user_id != current_user.id:
                    logger.info(f"🔍 [CREATE_CONVERSATION] Broadcasting new_conversation event to user: {user_id}")
                    await manager.send_personal_message(new_conversation_event, user_id)
                    logger.info(f"✅ [CREATE_CONVERSATION] Successfully sent new_conversation event to user: {user_id}")
        except Exception as e:
            logger.error(f"❌ [CREATE_CONVERSATION] Error broadcasting new_conversation event: {str(e)}")
            # Don't fail the conversation creation if broadcasting fails
        
        # Return conversation with participants
        return conversation_details
        
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")

@router.get("/conversations", response_model=ConversationsResponse)
async def get_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search query to match against participant names"),
    current_user = Depends(get_current_user)
):
    """Get user's conversations with pagination and optional search"""
    try:
        offset = (page - 1) * limit
        
        # If search query is provided, we need to search against participant names
        if q and q.strip():
            search_query = q.strip()
            
            # Get all conversations where user is a participant
            user_conversations_result = supabase_client.table('conversation_participants')\
                .select('conversation_id')\
                .eq('user_id', current_user.id)\
                .is_('left_at', 'null')\
                .execute()
            
            if not user_conversations_result.data:
                return ConversationsResponse(
                    conversations=[],
                    hasMore=False,
                    total=0
                )
            
            user_conversation_ids = [cp['conversation_id'] for cp in user_conversations_result.data]
            
            # Get all participants in these conversations
            participants_result = supabase_client.table('conversation_participants')\
                .select('conversation_id, user_id')\
                .in_('conversation_id', user_conversation_ids)\
                .is_('left_at', 'null')\
                .execute()
            
            if not participants_result.data:
                return ConversationsResponse(
                    conversations=[],
                    hasMore=False,
                    total=0
                )
            
            # Get all user IDs from participants
            participant_user_ids = list(set([cp['user_id'] for cp in participants_result.data]))
            
            # Search profiles for names matching the query
            matching_user_ids = set()
            
            # Search by first name
            first_name_profiles = supabase_client.table('profiles')\
                .select('id')\
                .in_('id', participant_user_ids)\
                .ilike('first_name', f'%{search_query}%')\
                .execute()
            
            if first_name_profiles.data:
                matching_user_ids.update([p['id'] for p in first_name_profiles.data])
            
            # Search by last name
            last_name_profiles = supabase_client.table('profiles')\
                .select('id')\
                .in_('id', participant_user_ids)\
                .ilike('last_name', f'%{search_query}%')\
                .execute()
            
            if last_name_profiles.data:
                matching_user_ids.update([p['id'] for p in last_name_profiles.data])
            
            # Search by full name (first_name + " " + last_name)
            # We need to get all profiles and check the concatenated name in Python
            all_profiles = supabase_client.table('profiles')\
                .select('id, first_name, last_name')\
                .in_('id', participant_user_ids)\
                .execute()
            
            if all_profiles.data:
                for profile in all_profiles.data:
                    first_name = profile.get('first_name', '') or ''
                    last_name = profile.get('last_name', '') or ''
                    full_name = f"{first_name} {last_name}".strip()
                    
                    # Check if the search query matches the full name
                    if search_query.lower() in full_name.lower():
                        matching_user_ids.add(profile['id'])
            
            if not matching_user_ids:
                return ConversationsResponse(
                    conversations=[],
                    hasMore=False,
                    total=0
                )
            
            # Get conversation IDs that contain these matching users
            matching_conversation_ids = set()
            for participant in participants_result.data:
                if participant['user_id'] in matching_user_ids:
                    matching_conversation_ids.add(participant['conversation_id'])
            
            if not matching_conversation_ids:
                return ConversationsResponse(
                    conversations=[],
                    hasMore=False,
                    total=0
                )
            
            # Get total count for search results
            total = len(matching_conversation_ids)
            
            # Get conversations with proper ordering and pagination
            result = supabase_client.table('conversations')\
                .select('*')\
                .in_('id', list(matching_conversation_ids))\
                .eq('is_deleted', False)\
                .order('last_message_at', desc=True)\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
        else:
            # No search query - use existing logic
            # First, get the total count of conversations where user is a participant
            total_count_result = supabase_client.table('conversation_participants')\
                .select('conversation_id', count='exact')\
                .eq('user_id', current_user.id)\
                .is_('left_at', 'null')\
                .execute()
            
            total = total_count_result.count or 0
            
            # Get conversations where user is a participant with proper pagination
            conversations_result = supabase_client.table('conversation_participants')\
                .select('conversation_id')\
                .eq('user_id', current_user.id)\
                .is_('left_at', 'null')\
                .execute()
            
            if not conversations_result.data:
                return ConversationsResponse(
                    conversations=[],
                    hasMore=False,
                    total=0
                )
            
            # Get the conversation IDs where user is a participant
            conversation_ids = [cp['conversation_id'] for cp in conversations_result.data]
            
            # Get conversations with proper ordering and pagination
            result = supabase_client.table('conversations')\
                .select('*')\
                .in_('id', conversation_ids)\
                .eq('is_deleted', False)\
                .order('last_message_at', desc=True)\
                .order('created_at', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
        
        conversations = []
        for conv in result.data:
            # Get participants for this conversation
            participants = supabase_client.table('conversation_participants')\
                .select('*, profiles(first_name, last_name, role)')\
                .eq('conversation_id', conv['id'])\
                .is_('left_at', 'null')\
                .execute()
            
            # Get unread count for this specific conversation
            # Count messages with status 'sent' that were not sent by the current user
            unread_result = supabase_client.table('message_status')\
                .select('message_id')\
                .eq('user_id', current_user.id)\
                .eq('status', 'sent')\
                .execute()
            
            if unread_result.data:
                # Get the message IDs that are unread
                unread_message_ids = [status['message_id'] for status in unread_result.data]
                
                # Count how many of these unread messages are in this conversation and not sent by current user
                unread_count_result = supabase_client.table('messages')\
                    .select('*', count='exact')\
                    .in_('id', unread_message_ids)\
                    .eq('conversation_id', conv['id'])\
                    .neq('sender_id', current_user.id)\
                    .eq('is_deleted', False)\
                    .execute()
                
                unread_count = unread_count_result.count or 0
            else:
                unread_count = 0
            
            conv['participants'] = participants.data
            conv['unread_count'] = unread_count
            conversations.append(conv)
        
        # Calculate hasMore based on total count and current page
        hasMore = total > (page * limit)
        
        return ConversationsResponse(
            conversations=conversations,
            hasMore=hasMore,
            total=total
        )
        
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
            .select('*, profiles(first_name, last_name, role)')\
            .eq('conversation_id', conversation_id)\
            .is_('left_at', 'null')\
            .execute()
        
        # Get unread count for this specific conversation
        # Count messages with status 'sent' that were not sent by the current user
        unread_result = supabase_client.table('message_status')\
            .select('message_id')\
            .eq('user_id', current_user.id)\
            .eq('status', 'sent')\
            .execute()
        
        if unread_result.data:
            # Get the message IDs that are unread
            unread_message_ids = [status['message_id'] for status in unread_result.data]
            
            # Count how many of these unread messages are in this conversation and not sent by current user
            unread_count_result = supabase_client.table('messages')\
                .select('*', count='exact')\
                .in_('id', unread_message_ids)\
                .eq('conversation_id', conversation_id)\
                .neq('sender_id', current_user.id)\
                .eq('is_deleted', False)\
                .execute()
            
            unread_count = unread_count_result.count or 0
        else:
            unread_count = 0
        
        conversation['participants'] = participants.data
        conversation['unread_count'] = unread_count
        
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
    """Delete conversation and all related data (hard delete)"""
    logger.info(f"🔍 [DELETE_CONVERSATION] User {current_user.id} attempting to delete conversation {conversation_id}")
    
    try:
        # Check if conversation exists
        conversation_result = supabase_client.table('conversations')\
            .select('*')\
            .eq('id', conversation_id)\
            .execute()
        
        if not conversation_result.data:
            logger.warning(f"⚠️ [DELETE_CONVERSATION] Conversation {conversation_id} not found")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation = conversation_result.data[0]
        logger.info(f"🔍 [DELETE_CONVERSATION] Found conversation: created_by={conversation['created_by']}, type={conversation.get('type')}")
        
        # Check if user is creator or admin
        participant_check = supabase_client.table('conversation_participants')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .is_('left_at', 'null')\
            .execute()
        
        if not participant_check.data:
            logger.warning(f"⚠️ [DELETE_CONVERSATION] User {current_user.id} is not a participant in conversation {conversation_id}")
            raise HTTPException(status_code=403, detail="Not a participant in this conversation")
        
        participant = participant_check.data[0]
        is_creator = conversation['created_by'] == current_user.id
        is_admin = participant['role'] in ['admin', 'moderator']
        
        if not (is_creator or is_admin):
            logger.warning(f"⚠️ [DELETE_CONVERSATION] User {current_user.id} lacks permission to delete conversation {conversation_id}. Role: {participant['role']}, Is Creator: {is_creator}")
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete this conversation")
        
        logger.info(f"✅ [DELETE_CONVERSATION] User {current_user.id} authorized to delete conversation {conversation_id}")
        
        # Get all participants for WebSocket notification
        participants_result = supabase_client.table('conversation_participants')\
            .select('user_id')\
            .eq('conversation_id', conversation_id)\
            .is_('left_at', 'null')\
            .execute()
        
        participant_user_ids = [p['user_id'] for p in participants_result.data] if participants_result.data else []
        logger.info(f"🔍 [DELETE_CONVERSATION] Found {len(participant_user_ids)} participants to notify")
        
        # Get all message IDs for deletion
        messages_result = supabase_client.table('messages')\
            .select('id')\
            .eq('conversation_id', conversation_id)\
            .execute()
        
        message_ids = [msg['id'] for msg in messages_result.data] if messages_result.data else []
        logger.info(f"🔍 [DELETE_CONVERSATION] Found {len(message_ids)} messages to delete")
        
        # Perform database operations in sequence (Supabase doesn't support transactions in the same way)
        # Delete message status records first (foreign key dependency)
        if message_ids:
            logger.info(f"🔍 [DELETE_CONVERSATION] Deleting {len(message_ids)} message status records")
            delete_status_result = supabase_client.table('message_status')\
                .delete()\
                .in_('message_id', message_ids)\
                .execute()
            logger.info(f"✅ [DELETE_CONVERSATION] Deleted message status records: {delete_status_result.data}")
        
        # Delete messages
        if message_ids:
            logger.info(f"🔍 [DELETE_CONVERSATION] Deleting {len(message_ids)} messages")
            delete_messages_result = supabase_client.table('messages')\
                .delete()\
                .in_('id', message_ids)\
                .execute()
            logger.info(f"✅ [DELETE_CONVERSATION] Deleted messages: {delete_messages_result.data}")
        
        # Delete conversation participants
        logger.info(f"🔍 [DELETE_CONVERSATION] Deleting conversation participants")
        delete_participants_result = supabase_client.table('conversation_participants')\
            .delete()\
            .eq('conversation_id', conversation_id)\
            .execute()
        logger.info(f"✅ [DELETE_CONVERSATION] Deleted conversation participants: {delete_participants_result.data}")
        
        # Delete the conversation
        logger.info(f"🔍 [DELETE_CONVERSATION] Deleting conversation {conversation_id}")
        delete_conversation_result = supabase_client.table('conversations')\
            .delete()\
            .eq('id', conversation_id)\
            .execute()
        logger.info(f"✅ [DELETE_CONVERSATION] Deleted conversation: {delete_conversation_result.data}")
        
        # Broadcast WebSocket event to all participants
        if participant_user_ids:
            deletion_event = {
                'type': 'conversation_deleted',
                'conversation_id': conversation_id,
                'deleted_by': current_user.id,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"🔍 [DELETE_CONVERSATION] Broadcasting deletion event to {len(participant_user_ids)} participants")
            try:
                # Send to each participant individually since they might not be in the conversation room anymore
                for user_id in participant_user_ids:
                    if user_id != current_user.id:  # Don't send to the user who deleted it
                        await manager.send_personal_message(deletion_event, user_id)
                        logger.info(f"✅ [DELETE_CONVERSATION] Sent deletion event to user {user_id}")
            except Exception as broadcast_error:
                logger.error(f"❌ [DELETE_CONVERSATION] Error broadcasting deletion event: {str(broadcast_error)}")
                # Don't fail the request if broadcasting fails
        
        logger.info(f"✅ [DELETE_CONVERSATION] Successfully deleted conversation {conversation_id} and all related data")
        
        # Return 204 No Content
        return Response(status_code=204)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [DELETE_CONVERSATION] Unexpected error deleting conversation {conversation_id}: {str(e)}")
        logger.error(f"❌ [DELETE_CONVERSATION] Error traceback: {traceback.format_exc()}")
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
        logger.info(f"🔍 [SEND_MESSAGE] Message created with ID: {message_id}")
        
        # Create message status entries for all participants FIRST
        logger.info(f"🔍 [SEND_MESSAGE] Creating message status entries for message_id: {message_id}")
        participants = supabase_client.table('conversation_participants')\
            .select('user_id')\
            .eq('conversation_id', conversation_id)\
            .is_('left_at', 'null')\
            .execute()
        
        logger.info(f"🔍 [SEND_MESSAGE] Found {len(participants.data)} participants for conversation {conversation_id}")
        logger.info(f"🔍 [SEND_MESSAGE] Participants data: {participants.data}")
        
        if participants.data:
            status_entries = []
            for participant in participants.data:
                # Create status entry for all participants
                # All participants start with 'sent' status when message is created
                status_entry = {
                    'message_id': message_id,
                    'user_id': participant['user_id'],
                    'status': 'sent'
                }
                status_entries.append(status_entry)
                logger.info(f"🔍 [SEND_MESSAGE] Created status entry: message_id={message_id}, user_id={participant['user_id']}, status=sent")
            
            logger.info(f"🔍 [SEND_MESSAGE] Total status entries to process: {len(status_entries)}")
            
            if status_entries:
                try:
                    # For new messages, we should always create fresh status entries
                    # First, delete any existing status entries for this message to ensure clean state
                    logger.info(f"🔍 [SEND_MESSAGE] Deleting any existing status entries for message_id: {message_id}")
                    delete_result = supabase_client.table('message_status')\
                        .delete()\
                        .eq('message_id', message_id)\
                        .execute()
                    logger.info(f"🔍 [SEND_MESSAGE] Delete result: {delete_result.data}")
                    
                    # Now insert fresh status entries with 'sent' status
                    for status_entry in status_entries:
                        logger.info(f"🔍 [SEND_MESSAGE] Processing status entry: {status_entry}")
                        
                        # Insert fresh status entry
                        logger.info(f"🔍 [SEND_MESSAGE] About to insert status entry: {status_entry}")
                        insert_result = supabase_client.table('message_status').insert(status_entry).execute()
                        logger.info(f"✅ [SEND_MESSAGE] Successfully inserted status entry: message_id={status_entry['message_id']}, user_id={status_entry['user_id']}, status={status_entry['status']}")
                        logger.info(f"🔍 [SEND_MESSAGE] Insert result: {insert_result.data}")
                    
                except Exception as status_error:
                    logger.error(f"❌ [SEND_MESSAGE] Error creating message status entries: {str(status_error)}")
                    logger.error(f"❌ [SEND_MESSAGE] Error type: {type(status_error)}")
                    logger.error(f"❌ [SEND_MESSAGE] Error traceback: {traceback.format_exc()}")
                    # Don't fail the entire request if status creation fails
        else:
            logger.warning(f"⚠️ [SEND_MESSAGE] No participants found for conversation {conversation_id}")
        
        # Check what's in message_status table after our operations
        try:
            status_check = supabase_client.table('message_status')\
                .select('*')\
                .eq('message_id', message_id)\
                .execute()
            logger.info(f"🔍 [SEND_MESSAGE] Message status table contents after operations: {status_check.data}")
            
            # Check specifically for current user's status
            current_user_status = supabase_client.table('message_status')\
                .select('*')\
                .eq('message_id', message_id)\
                .eq('user_id', current_user.id)\
                .execute()
            logger.info(f"🔍 [SEND_MESSAGE] Current user status specifically: {current_user_status.data}")
            
        except Exception as check_error:
            logger.error(f"❌ [SEND_MESSAGE] Error checking message status table: {str(check_error)}")
        
        # Update conversation's last_message_at
        supabase_client.table('conversations')\
            .update({'last_message_at': datetime.now().isoformat()})\
            .eq('id', conversation_id)\
            .execute()
        
        # Get full message with sender info AFTER status entries are created
        logger.info(f"🔍 [SEND_MESSAGE] About to call get_message_details for message_id: {message_id}, current_user: {current_user.id}")
        full_message = await get_message_details(message_id, current_user)
        logger.info(f"🔍 [SEND_MESSAGE] get_message_details returned status: {full_message.status}")
        
        # For newly sent messages, the sender's status should always be 'sent', not 'read'
        # This ensures that even if there are existing status entries, we override them
        if full_message.sender_id == current_user.id:
            # Force the status to 'sent' for the sender of a newly created message
            full_message.status = 'sent'
            logger.info(f"🔍 [SEND_MESSAGE] Forced sender status to 'sent' for newly created message")
        
        logger.info(f"🔍 [SEND_MESSAGE] About to return MessageResponse with status: {full_message.status}")
        
        # Broadcast to conversation participants via WebSocket
        broadcast_message = {
            'type': 'new_message',
            'message': full_message.dict(),
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"🔍 [SEND_MESSAGE] About to broadcast message with status: {full_message.status}")
        try:
            await manager.broadcast_to_conversation(broadcast_message, conversation_id, current_user.id)
            logger.info(f"🔍 [SEND_MESSAGE] Successfully broadcasted message")
        except Exception as broadcast_error:
            logger.error(f"Failed to broadcast message: {str(broadcast_error)}")
            # Don't fail the request if broadcasting fails
        
        logger.info(f"🔍 [SEND_MESSAGE] Final return - MessageResponse with status: {full_message.status}")
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
    """Get conversation messages with pagination
    
    Pagination Logic:
    - Page 1: Returns the most recent 50 messages (latest messages)
    - Page 2+: Returns older messages (previous 50 messages)
    - Messages are returned in chronological order (oldest first, newest last)
    - This allows infinite scroll from bottom to top
    """
    logger.info(f"🔍 [GET_MESSAGES] Getting messages for conversation_id: {conversation_id}, page: {page}, limit: {limit}, current_user: {current_user.id}")
    
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
        
        # Get total count first
        total_count_result = supabase_client.table('messages')\
            .select('*', count='exact')\
            .eq('conversation_id', conversation_id)\
            .eq('is_deleted', False)\
            .execute()
        
        total = total_count_result.count or 0
        
        # Calculate pagination for reverse chronological order
        # For infinite scroll from bottom to top:
        # Page 1: Most recent messages (offset from end)
        # Page 2+: Older messages (previous offset from end)
        offset_from_end = (page - 1) * limit
        
        # Get messages in reverse chronological order (newest first for pagination)
        # Then we'll reverse them to get chronological order (oldest first)
        result = supabase_client.table('messages')\
            .select('*')\
            .eq('conversation_id', conversation_id)\
            .eq('is_deleted', False)\
            .order('created_at', desc=True)\
            .range(offset_from_end, offset_from_end + limit - 1)\
            .execute()
        
        # Process messages and reverse order to get chronological (oldest first)
        messages = []
        logger.info(f"🔍 [GET_MESSAGES] Processing {len(result.data)} messages")
        for msg in reversed(result.data):  # Reverse to get chronological order
            try:
                logger.info(f"🔍 [GET_MESSAGES] Processing message_id: {msg['id']}")
                message_details = await get_message_details(msg['id'], current_user)
                logger.info(f"🔍 [GET_MESSAGES] Message {msg['id']} final status: {message_details.status}")
                messages.append(message_details)
            except Exception as msg_error:
                logger.error(f"❌ [GET_MESSAGES] Error processing message {msg.get('id', 'unknown')}: {str(msg_error)}")
                # Continue with other messages instead of failing completely
                continue
        
        # Calculate if there are more messages (older messages available)
        has_more = (offset_from_end + limit) < total
        
        return MessagesResponse(
            messages=messages,
            hasMore=has_more,
            total=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get messages")

async def get_message_details(message_id: str, current_user):
    """Helper function to get message details with sender info"""
    logger.info(f"🔍 [GET_MESSAGE_DETAILS] Getting details for message_id: {message_id}, current_user: {current_user.id}")
    
    try:
        result = supabase_client.table('messages')\
            .select('*')\
            .eq('id', message_id)\
            .execute()
        
        if not result.data:
            logger.error(f"❌ [GET_MESSAGE_DETAILS] Message not found: {message_id}")
            raise HTTPException(status_code=404, detail="Message not found")
        
        message = result.data[0]
        logger.info(f"🔍 [GET_MESSAGE_DETAILS] Message data retrieved: sender_id={message.get('sender_id')}, content={message.get('content', '')[:50]}...")
        
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
                else:
                    message_data['sender_name'] = "Unknown User"
            except Exception as sender_error:
                logger.error(f"Error getting sender info: {str(sender_error)}")
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
            except Exception as reply_error:
                logger.error(f"Error getting reply content: {str(reply_error)}")
        
        # Get message status for current user
        try:
            logger.info(f"🔍 [GET_MESSAGE_DETAILS] Querying message_status for message_id: {message_id}, user_id: {current_user.id}")
            status = supabase_client.table('message_status')\
                .select('status')\
                .eq('message_id', message_id)\
                .eq('user_id', current_user.id)\
                .execute()
            
            logger.info(f"🔍 [GET_MESSAGE_DETAILS] Status query result: {status.data}")
            
            if status.data:
                retrieved_status = status.data[0].get('status', 'sent')
                logger.info(f"✅ [GET_MESSAGE_DETAILS] Found status record: {retrieved_status}")
                message_data['status'] = retrieved_status
            else:
                # If no status record exists, default to 'sent'
                message_data['status'] = 'sent'
                logger.info(f"⚠️ [GET_MESSAGE_DETAILS] No status record found, defaulting to 'sent'")
        except Exception as status_error:
            logger.error(f"❌ [GET_MESSAGE_DETAILS] Error getting message status: {str(status_error)}")
            # If error occurs, default to 'sent'
            message_data['status'] = 'sent'
        
        logger.info(f"🔍 [GET_MESSAGE_DETAILS] Final message status: {message_data['status']}")
        
        # Create MessageResponse and log the final status
        message_response = MessageResponse(**message_data)
        logger.info(f"🔍 [GET_MESSAGE_DETAILS] MessageResponse created with status: {message_response.status}")
        
        return message_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message details: {str(e)}")
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

@router.post("/messages/{message_id}/delivered")
async def mark_message_delivered(
    message_id: str,
    current_user = Depends(get_current_user)
):
    """Mark message as delivered"""
    try:
        # Update message status to delivered
        supabase_client.table('message_status')\
            .update({'status': 'delivered'})\
            .eq('message_id', message_id)\
            .eq('user_id', current_user.id)\
            .execute()
        
        return {"message": "Message marked as delivered"}
        
    except Exception as e:
        logger.error(f"Error marking message as delivered: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark message as delivered")

@router.post("/messages/{message_id}/read")
async def mark_message_read(
    message_id: str,
    current_user = Depends(get_current_user)
):
    """Mark message as read"""
    try:
        # Update message status to read
        supabase_client.table('message_status')\
            .update({'status': 'read'})\
            .eq('message_id', message_id)\
            .eq('user_id', current_user.id)\
            .execute()
        
        return {"message": "Message marked as read"}
        
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark message as read")

@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: str,
    current_user = Depends(get_current_user)
):
    """Mark all messages in a conversation as read for the current user"""
    logger.info(f"🔍 [MARK_CONVERSATION_READ] Called for conversation_id: {conversation_id}, user_id: {current_user.id}")
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
        
        # Update conversation_participants.last_read_at
        supabase_client.table('conversation_participants')\
            .update({'last_read_at': datetime.now().isoformat()})\
            .eq('conversation_id', conversation_id)\
            .eq('user_id', current_user.id)\
            .execute()
        
        # Update all message_status entries for this user in this conversation to 'read'
        # First get all messages in the conversation
        messages_result = supabase_client.table('messages')\
            .select('id')\
            .eq('conversation_id', conversation_id)\
            .eq('is_deleted', False)\
            .execute()
        
        if messages_result.data:
            message_ids = [msg['id'] for msg in messages_result.data]
            
            # Update message_status for all these messages for the current user
            # Only update messages that are currently 'sent' or 'delivered' to 'read'
            logger.info(f"🔍 [MARK_CONVERSATION_READ] Updating {len(message_ids)} messages to 'read' status")
            for message_id in message_ids:
                logger.info(f"🔍 [MARK_CONVERSATION_READ] Updating message_id: {message_id} to 'read' for user_id: {current_user.id}")
                result = supabase_client.table('message_status')\
                    .update({'status': 'read'})\
                    .eq('message_id', message_id)\
                    .eq('user_id', current_user.id)\
                    .in_('status', ['sent', 'delivered'])\
                    .execute()
                logger.info(f"🔍 [MARK_CONVERSATION_READ] Update result for message_id {message_id}: {result.data}")
        
        # Broadcast WebSocket event to notify other participants
        read_event = {
            'type': 'message_read',
            'conversation_id': conversation_id,
            'user_id': current_user.id,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            await manager.broadcast_to_conversation(read_event, conversation_id, current_user.id)
        except Exception as broadcast_error:
            logger.error(f"Error broadcasting read event: {str(broadcast_error)}")
            # Don't fail the request if broadcasting fails
        
        return {"message": "Conversation marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking conversation as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark conversation as read")

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
            .select('*, profiles(first_name, last_name, role)')\
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
        result = supabase_client.table('user_status')\
            .select('*')\
            .in_('user_id', user_ids)\
            .execute()
        
        return result.data
        
    except Exception as e:
        logger.error(f"Error getting users status: {str(e)}")
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
        
        return {"message": "Status updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating user status: {str(e)}")
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
        # Authenticate user BEFORE accepting connection
        try:
            response = supabase_client.auth.get_user(token)
            if not response.user:
                # Don't accept connection if token is invalid
                return
            user_id = response.user.id
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            # Don't accept connection if authentication fails
            return
        
        # Accept the connection only after successful authentication
        await websocket.accept()
        connection_accepted = True
        
        # Connect user to manager (this will update status to online in database)
        await manager.connect(websocket, user_id)
        
        # Send connection confirmation
        await websocket.send_json({
            'type': 'connection_established',
            'user_id': user_id,
            'message': 'WebSocket connection established'
        })
        
        # Automatically join user to all their active conversations
        try:
            conversations = supabase_client.table('conversation_participants')\
                .select('conversation_id')\
                .eq('user_id', user_id)\
                .is_('left_at', 'null')\
                .execute()
            
            if conversations.data:
                for conv in conversations.data:
                    conversation_id = conv['conversation_id']
                    await manager.join_conversation(user_id, conversation_id)
                
                await websocket.send_json({
                    'type': 'auto_joined_conversations',
                    'conversation_ids': [conv['conversation_id'] for conv in conversations.data],
                    'message': f'Auto-joined {len(conversations.data)} conversations'
                })
        except Exception as e:
            logger.error(f"Error auto-joining conversations: {str(e)}")
            # Don't fail the connection if auto-join fails
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_websocket_message(websocket, user_id, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Message handling error: {str(e)}")
                if connection_accepted:
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Invalid message format',
                        'error': str(e)
                    })
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        if user_id:
            manager.disconnect(user_id)

async def handle_websocket_message(websocket: WebSocket, user_id: str, data: dict):
    """Handle incoming WebSocket messages"""
    message_type = data.get('type')
    
    try:
        if message_type == 'join_conversation':
            conversation_id = data.get('conversation_id')
            
            if conversation_id:
                # Verify user is participant in conversation
                try:
                    participant_check = supabase_client.table('conversation_participants')\
                        .select('*')\
                        .eq('conversation_id', conversation_id)\
                        .eq('user_id', user_id)\
                        .is_('left_at', 'null')\
                        .execute()
                    
                    if participant_check.data:
                        await manager.join_conversation(user_id, conversation_id)
                        await websocket.send_json({
                            'type': 'joined_conversation',
                            'conversation_id': conversation_id,
                            'user_id': user_id
                        })
                    else:
                        await websocket.send_json({
                            'type': 'error',
                            'message': 'Not a participant in this conversation'
                        })
                except Exception as e:
                    logger.error(f"Error checking participant status: {str(e)}")
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Error checking participant status',
                        'error': str(e)
                    })
            else:
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
        
        elif message_type == 'typing_start':
            conversation_id = data.get('conversation_id')
            if conversation_id:
                # Update status in database and memory
                await manager.update_user_status_in_database(user_id, 'online', True, conversation_id)
                await manager.update_user_status(user_id, 'online', True, conversation_id)
                await manager.broadcast_to_conversation({
                    'type': 'typing_start',
                    'user_id': user_id,
                    'conversation_id': conversation_id,
                    'timestamp': datetime.now().isoformat()
                }, conversation_id, user_id)
        
        elif message_type == 'typing_stop':
            conversation_id = data.get('conversation_id')
            if conversation_id:
                # Update status in database and memory
                await manager.update_user_status_in_database(user_id, 'online', False, None)
                await manager.update_user_status(user_id, 'online', False, None)
                await manager.broadcast_to_conversation({
                    'type': 'typing_stop',
                    'user_id': user_id,
                    'conversation_id': conversation_id,
                    'timestamp': datetime.now().isoformat()
                }, conversation_id, user_id)
        
        elif message_type == 'message_delivered':
            message_id = data.get('message_id')
            conversation_id = data.get('conversation_id')
            if message_id and conversation_id:
                try:
                    # Update message status to delivered
                    supabase_client.table('message_status')\
                        .update({'status': 'delivered'})\
                        .eq('message_id', message_id)\
                        .eq('user_id', user_id)\
                        .execute()
                    
                    # Broadcast delivery receipt
                    await manager.broadcast_to_conversation({
                        'type': 'message_delivered',
                        'message_id': message_id,
                        'user_id': user_id,
                        'conversation_id': conversation_id,
                        'timestamp': datetime.now().isoformat()
                    }, conversation_id, user_id)
                except Exception as e:
                    logger.error(f"Error marking message as delivered: {str(e)}")
        
        elif message_type == 'message_read':
            message_id = data.get('message_id')
            conversation_id = data.get('conversation_id')
            logger.info(f"🔍 [WEBSOCKET] Received message_read event for message_id: {message_id}, user_id: {user_id}")
            if message_id and conversation_id:
                try:
                    # Update message status to read
                    logger.info(f"🔍 [WEBSOCKET] About to update message_status to 'read' for message_id: {message_id}, user_id: {user_id}")
                    supabase_client.table('message_status')\
                        .update({'status': 'read'})\
                        .eq('message_id', message_id)\
                        .eq('user_id', user_id)\
                        .execute()
                    logger.info(f"✅ [WEBSOCKET] Successfully updated message_status to 'read' for message_id: {message_id}, user_id: {user_id}")
                    
                    # Broadcast read receipt
                    await manager.broadcast_to_conversation({
                        'type': 'message_read',
                        'message_id': message_id,
                        'user_id': user_id,
                        'conversation_id': conversation_id,
                        'timestamp': datetime.now().isoformat()
                    }, conversation_id, user_id)
                except Exception as e:
                    logger.error(f"Error marking message as read: {str(e)}")
        
        elif message_type == 'user_status_change':
            status = data.get('status')
            is_typing = data.get('is_typing', False)
            typing_in_conversation = data.get('typing_in_conversation')
            
            if status and status in ['online', 'offline', 'away', 'busy']:
                # Update status in database and memory
                await manager.update_user_status_in_database(user_id, status, is_typing, typing_in_conversation)
                await manager.update_user_status(user_id, status, is_typing, typing_in_conversation)
            else:
                await websocket.send_json({
                    'type': 'error',
                    'message': 'Invalid status value'
                })
        
        elif message_type == 'ping':
            # Handle ping for connection health check
            await websocket.send_json({
                'type': 'pong',
                'timestamp': datetime.now().isoformat()
            })
        
        else:
            await websocket.send_json({
                'type': 'error',
                'message': f'Unknown message type: {message_type}',
                'supported_types': ['join_conversation', 'leave_conversation', 'typing_start', 'typing_stop', 'message_delivered', 'message_read', 'user_status_change', 'ping']
            })
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {str(e)}")
        await websocket.send_json({
            'type': 'error',
            'message': 'Internal server error',
            'error': str(e)
        })



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
