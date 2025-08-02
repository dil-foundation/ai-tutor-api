# Messaging System Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [WebSocket Events](#websocket-events)
5. [Authentication](#authentication)
6. [Rate Limiting](#rate-limiting)
7. [Data Models](#data-models)
8. [Usage Examples](#usage-examples)
9. [Integration Guide](#integration-guide)
10. [Error Handling](#error-handling)
11. [Performance Considerations](#performance-considerations)
12. [Security](#security)
13. [Testing](#testing)

## 🎯 Overview

The Messaging System is a comprehensive real-time communication platform built with FastAPI and WebSockets. It provides:

- **Real-time messaging** with WebSocket support
- **Conversation management** (direct and group chats)
- **Message persistence** in Supabase database
- **Read receipts** and typing indicators
- **Online/offline status** tracking
- **File upload** support
- **Role-based permissions** (admin, moderator, participant)
- **Rate limiting** to prevent abuse
- **Message threading** and replies

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  WebSocket      │    │   Supabase      │
│                 │    │  Manager        │    │   Database      │
│ - REST API      │◄──►│ - Connections   │◄──►│ - Conversations │
│ - Authentication│    │ - Broadcasting  │    │ - Messages      │
│ - Rate Limiting │    │ - Status Mgmt   │    │ - Participants  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Cache   │    │   Rate Limiter  │    │   File Storage  │
│ - Session Mgmt  │    │ - API Limits    │    │ - Images/Files  │
│ - Temp Data     │    │ - WebSocket     │    │ - Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Database Schema

The system uses 5 main tables in Supabase:

1. **`conversations`** - Conversation metadata
2. **`conversation_participants`** - Participant management
3. **`messages`** - Message storage
4. **`message_status`** - Read receipts
5. **`user_status`** - Online status

## 🔌 API Endpoints

### Conversation Management

#### Create Conversation
```http
POST /api/conversations
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "Study Group",
  "type": "group",
  "participant_ids": ["user-1", "user-2", "user-3"]
}
```

**Response:**
```json
{
  "id": "conv-123",
  "title": "Study Group",
  "type": "group",
  "created_by": "user-1",
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z",
  "last_message_at": "2024-01-20T10:00:00Z",
  "is_archived": false,
  "is_deleted": false,
  "participants": [...],
  "unread_count": 0
}
```

#### Get Conversations
```http
GET /api/conversations?page=1&limit=50
Authorization: Bearer <token>
```

#### Get Conversation Details
```http
GET /api/conversations/{conversation_id}
Authorization: Bearer <token>
```

#### Update Conversation
```http
PUT /api/conversations/{conversation_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "Updated Title",
  "is_archived": false
}
```

#### Delete Conversation
```http
DELETE /api/conversations/{conversation_id}
Authorization: Bearer <token>
```

### Message Management

#### Send Message
```http
POST /api/conversations/{conversation_id}/messages
Content-Type: application/json
Authorization: Bearer <token>

{
  "content": "Hello, everyone!",
  "message_type": "text",
  "reply_to_id": "msg-123",
  "metadata": {
    "emoji": "👋"
  }
}
```

**Response:**
```json
{
  "id": "msg-456",
  "conversation_id": "conv-123",
  "sender_id": "user-1",
  "sender_name": "John Doe",
  "content": "Hello, everyone!",
  "message_type": "text",
  "reply_to_id": "msg-123",
  "reply_to_content": "Previous message",
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z",
  "is_edited": false,
  "is_deleted": false,
  "metadata": {"emoji": "👋"},
  "status": "sent"
}
```

#### Get Messages
```http
GET /api/conversations/{conversation_id}/messages?page=1&limit=50
Authorization: Bearer <token>
```

#### Edit Message
```http
PUT /api/messages/{message_id}
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

content=Updated message content
```

#### Delete Message
```http
DELETE /api/messages/{message_id}
Authorization: Bearer <token>
```

#### Mark Message as Read
```http
POST /api/messages/{message_id}/read
Authorization: Bearer <token>
```

### Participant Management

#### Add Participant
```http
POST /api/conversations/{conversation_id}/participants
Content-Type: application/json
Authorization: Bearer <token>

{
  "user_id": "user-4",
  "role": "participant"
}
```

#### Remove Participant
```http
DELETE /api/conversations/{conversation_id}/participants/{user_id}
Authorization: Bearer <token>
```

#### Update Participant
```http
PUT /api/conversations/{conversation_id}/participants/{user_id}
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>

role=moderator&is_muted=false
```

### User Status

#### Get Users Status
```http
GET /api/users/status?user_ids=user-1&user_ids=user-2
Authorization: Bearer <token>
```

#### Update Own Status
```http
PUT /api/users/status
Content-Type: application/json
Authorization: Bearer <token>

{
  "status": "online",
  "is_typing": false,
  "typing_in_conversation": null
}
```

### File Upload

#### Upload File
```http
POST /api/conversations/{conversation_id}/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <file_data>
```

## 🔄 WebSocket Events

### Connection

Connect to WebSocket with authentication token:
```javascript
const ws = new WebSocket(`ws://localhost:8000/api/ws/${token}`);
```

### Client to Server Events

#### Join Conversation
```json
{
  "type": "join_conversation",
  "conversation_id": "conv-123"
}
```

#### Leave Conversation
```json
{
  "type": "leave_conversation",
  "conversation_id": "conv-123"
}
```

#### Typing Start
```json
{
  "type": "typing_start",
  "conversation_id": "conv-123"
}
```

#### Typing Stop
```json
{
  "type": "typing_stop",
  "conversation_id": "conv-123"
}
```

#### Mark Message as Read
```json
{
  "type": "message_read",
  "message_id": "msg-123",
  "conversation_id": "conv-123"
}
```

### Server to Client Events

#### New Message
```json
{
  "type": "new_message",
  "message": {
    "id": "msg-456",
    "conversation_id": "conv-123",
    "sender_id": "user-1",
    "sender_name": "John Doe",
    "content": "Hello!",
    "message_type": "text",
    "created_at": "2024-01-20T10:00:00Z",
    "status": "sent"
  }
}
```

#### User Status Change
```json
{
  "type": "user_status_change",
  "user_id": "user-1",
  "status": "online",
  "is_typing": true,
  "conversation_id": "conv-123"
}
```

#### Typing Indicators
```json
{
  "type": "typing_start",
  "user_id": "user-1",
  "conversation_id": "conv-123"
}
```

```json
{
  "type": "typing_stop",
  "user_id": "user-1",
  "conversation_id": "conv-123"
}
```

#### Message Read Receipt
```json
{
  "type": "message_read",
  "message_id": "msg-123",
  "user_id": "user-1"
}
```

#### Error Messages
```json
{
  "type": "error",
  "message": "Invalid message format"
}
```

## 🔐 Authentication

All API endpoints require authentication using Supabase JWT tokens:

### Token Format
```http
Authorization: Bearer <supabase_jwt_token>
```

### WebSocket Authentication
The WebSocket endpoint supports two authentication methods:

#### Method 1: Authorization Header (Recommended)
```javascript
// Connect with Authorization header
const ws = new WebSocket('ws://localhost:8000/api/ws', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

#### Method 2: Query Parameter (Fallback)
```javascript
// Connect with token in query parameter (for platforms that don't support headers)
const ws = new WebSocket(`ws://localhost:8000/api/ws?token=${token}`);
```

### Token Validation
The system validates tokens with Supabase and extracts user information:
- User ID
- Email
- Role permissions

## ⚡ Rate Limiting

The system implements comprehensive rate limiting:

### API Rate Limits
- **Message sending**: 10 messages per minute
- **Conversation creation**: 5 conversations per 5 minutes
- **File upload**: 3 files per minute
- **WebSocket connections**: 10 connections per minute
- **General API**: 100 requests per minute

### Role-Based Limits
- **Admin**: Higher limits (50 messages/min, 20 conversations/5min)
- **Moderator**: Medium limits (30 messages/min, 10 conversations/5min)
- **Teacher**: Moderate limits (20 messages/min, 8 conversations/5min)
- **Student**: Standard limits (10 messages/min, 5 conversations/5min)

### Rate Limit Headers
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 5
X-RateLimit-Reset: 1642672800
Retry-After: 30
```

### Rate Limit Response
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many message_send requests",
  "rate_limit_info": {
    "limit_type": "message_send",
    "current_count": 11,
    "limit": 10,
    "window": 60,
    "reset_time": 1642672800,
    "remaining": 0
  },
  "retry_after": 30
}
```

## 📊 Data Models

### Conversation Types
```python
class ConversationType(str, Enum):
    DIRECT = "direct"    # One-on-one conversation
    GROUP = "group"      # Multi-participant conversation
```

### Message Types
```python
class MessageType(str, Enum):
    TEXT = "text"        # Text message
    IMAGE = "image"      # Image file
    FILE = "file"        # Document/file
    SYSTEM = "system"    # System notification
```

### User Status Types
```python
class UserStatusType(str, Enum):
    ONLINE = "online"    # User is online
    OFFLINE = "offline"  # User is offline
    AWAY = "away"        # User is away
    BUSY = "busy"        # User is busy
```

### Participant Roles
```python
class ParticipantRole(str, Enum):
    PARTICIPANT = "participant"  # Regular participant
    ADMIN = "admin"              # Conversation admin
    MODERATOR = "moderator"      # Conversation moderator
```

## 💡 Usage Examples

### JavaScript/TypeScript Client

#### Basic Setup
```javascript
class MessagingClient {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.token = token;
        this.ws = null;
        this.conversations = new Map();
    }

    // Connect to WebSocket
    connect() {
        this.ws = new WebSocket(`${this.baseUrl}/api/ws`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });
        
        this.ws.onopen = () => {
            console.log('Connected to messaging system');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected from messaging system');
            // Implement reconnection logic
            setTimeout(() => this.connect(), 5000);
        };
    }

    // Handle incoming messages
    handleMessage(data) {
        switch (data.type) {
            case 'new_message':
                this.onNewMessage(data.message);
                break;
            case 'user_status_change':
                this.onUserStatusChange(data);
                break;
            case 'typing_start':
                this.onTypingStart(data);
                break;
            case 'typing_stop':
                this.onTypingStop(data);
                break;
            case 'message_read':
                this.onMessageRead(data);
                break;
            case 'error':
                console.error('WebSocket error:', data.message);
                break;
        }
    }

    // Join conversation
    joinConversation(conversationId) {
        this.send({
            type: 'join_conversation',
            conversation_id: conversationId
        });
    }

    // Send message
    async sendMessage(conversationId, content, replyToId = null) {
        const response = await fetch(`${this.baseUrl}/api/conversations/${conversationId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
                content,
                message_type: 'text',
                reply_to_id: replyToId
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to send message: ${response.statusText}`);
        }

        return await response.json();
    }

    // Start typing indicator
    startTyping(conversationId) {
        this.send({
            type: 'typing_start',
            conversation_id: conversationId
        });
    }

    // Stop typing indicator
    stopTyping(conversationId) {
        this.send({
            type: 'typing_stop',
            conversation_id: conversationId
        });
    }

    // Mark message as read
    markMessageRead(messageId, conversationId) {
        this.send({
            type: 'message_read',
            message_id: messageId,
            conversation_id: conversationId
        });
    }

    // Send WebSocket message
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    // Event handlers (to be implemented by user)
    onNewMessage(message) {
        console.log('New message:', message);
    }

    onUserStatusChange(data) {
        console.log('User status changed:', data);
    }

    onTypingStart(data) {
        console.log('User started typing:', data);
    }

    onTypingStop(data) {
        console.log('User stopped typing:', data);
    }

    onMessageRead(data) {
        console.log('Message read:', data);
    }
}
```

#### Usage Example
```javascript
// Initialize client
const client = new MessagingClient('http://localhost:8000', 'your-jwt-token');

// Connect to WebSocket
client.connect();

// Join a conversation
client.joinConversation('conv-123');

// Send a message
client.sendMessage('conv-123', 'Hello, everyone!')
    .then(message => console.log('Message sent:', message))
    .catch(error => console.error('Error sending message:', error));

// Start typing
client.startTyping('conv-123');

// Stop typing after 2 seconds
setTimeout(() => {
    client.stopTyping('conv-123');
}, 2000);
```

### React Hook Example
```javascript
import { useState, useEffect, useCallback } from 'react';

function useMessaging(token) {
    const [ws, setWs] = useState(null);
    const [messages, setMessages] = useState([]);
    const [typingUsers, setTypingUsers] = useState(new Set());
    const [isConnected, setIsConnected] = useState(false);

    // Connect to WebSocket
    const connect = useCallback(() => {
        const websocket = new WebSocket('ws://localhost:8000/api/ws', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        websocket.onopen = () => {
            setIsConnected(true);
            console.log('Connected to messaging');
        };
        
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleMessage(data);
        };
        
        websocket.onclose = () => {
            setIsConnected(false);
            console.log('Disconnected from messaging');
            // Reconnect after 5 seconds
            setTimeout(connect, 5000);
        };
        
        setWs(websocket);
    }, [token]);

    // Handle incoming messages
    const handleMessage = useCallback((data) => {
        switch (data.type) {
            case 'new_message':
                setMessages(prev => [data.message, ...prev]);
                break;
            case 'typing_start':
                setTypingUsers(prev => new Set(prev).add(data.user_id));
                break;
            case 'typing_stop':
                setTypingUsers(prev => {
                    const newSet = new Set(prev);
                    newSet.delete(data.user_id);
                    return newSet;
                });
                break;
        }
    }, []);

    // Send message
    const sendMessage = useCallback(async (conversationId, content) => {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ content, message_type: 'text' })
            });
            
            if (!response.ok) {
                throw new Error('Failed to send message');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }, [token]);

    // Join conversation
    const joinConversation = useCallback((conversationId) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'join_conversation',
                conversation_id: conversationId
            }));
        }
    }, [ws]);

    // Start typing
    const startTyping = useCallback((conversationId) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'typing_start',
                conversation_id: conversationId
            }));
        }
    }, [ws]);

    // Stop typing
    const stopTyping = useCallback((conversationId) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'typing_stop',
                conversation_id: conversationId
            }));
        }
    }, [ws]);

    useEffect(() => {
        connect();
        return () => {
            if (ws) {
                ws.close();
            }
        };
    }, [connect]);

    return {
        isConnected,
        messages,
        typingUsers,
        sendMessage,
        joinConversation,
        startTyping,
        stopTyping
    };
}
```

## 🔧 Integration Guide

### 1. Setup Database

Run the provided SQL schema to create the messaging tables in Supabase:

```sql
-- Run the complete messaging schema SQL
-- (See the provided database schema)
```

### 2. Configure Environment Variables

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Redis Configuration (for rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379

# File Upload Configuration
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=image/jpeg,image/png,image/gif,application/pdf,text/plain
```

### 3. Install Dependencies

```bash
pip install fastapi[websockets] supabase redis python-jose[cryptography] python-multipart
```

### 4. Initialize the System

```python
from app.routes.messaging import router
from app.middleware.rate_limiter import RateLimitMiddleware
from app.redis_client import redis_client

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

# Include messaging routes
app.include_router(router, prefix="/api", tags=["Messaging System"])
```

### 5. Client Integration

#### Frontend Setup
```javascript
// Install WebSocket client
npm install ws

// Initialize messaging client
const messagingClient = new MessagingClient(API_BASE_URL, userToken);
messagingClient.connect();
```

#### Mobile App Integration
```dart
// Flutter example
import 'package:web_socket_channel/web_socket_channel.dart';

class MessagingService {
  WebSocketChannel? _channel;
  
  void connect(String token) {
    // Note: Dart WebSocket doesn't support custom headers directly
    // Using query parameter as fallback method
    _channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8000/api/ws?token=$token'),
    );
    
    _channel!.stream.listen(
      (data) => handleMessage(jsonDecode(data)),
      onError: (error) => print('WebSocket error: $error'),
      onDone: () => print('WebSocket connection closed'),
    );
  }
  
  void sendMessage(Map<String, dynamic> data) {
    _channel?.sink.add(jsonEncode(data));
  }
}
```

## ⚠️ Error Handling

### Common Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Invalid token"
}
```

#### 403 Forbidden
```json
{
  "detail": "Not a participant in this conversation"
}
```

#### 404 Not Found
```json
{
  "detail": "Conversation not found"
}
```

#### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many message_send requests",
  "rate_limit_info": {
    "limit_type": "message_send",
    "current_count": 11,
    "limit": 10,
    "window": 60,
    "reset_time": 1642672800,
    "remaining": 0
  },
  "retry_after": 30
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to send message"
}
```

### Error Handling Best Practices

```javascript
class MessagingClient {
    async sendMessage(conversationId, content) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ content, message_type: 'text' })
            });

            if (response.status === 429) {
                const errorData = await response.json();
                const retryAfter = errorData.retry_after;
                console.log(`Rate limited. Retry after ${retryAfter} seconds`);
                return { error: 'rate_limited', retryAfter };
            }

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to send message');
            }

            return await response.json();
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }

    handleWebSocketError(error) {
        console.error('WebSocket error:', error);
        
        // Implement reconnection logic
        if (this.ws.readyState === WebSocket.CLOSED) {
            setTimeout(() => this.connect(), 5000);
        }
    }
}
```

## 🚀 Performance Considerations

### 1. Message Pagination
Always use pagination when loading messages:
```javascript
// Load messages in pages
const messages = await fetch(`/api/conversations/${conversationId}/messages?page=1&limit=50`);
```

### 2. WebSocket Connection Management
```javascript
// Implement connection pooling for multiple conversations
class ConnectionManager {
    constructor() {
        this.connections = new Map();
        this.maxConnections = 5;
    }

    getConnection(conversationId) {
        if (this.connections.size >= this.maxConnections) {
            // Close least recently used connection
            this.closeLRUConnection();
        }
        
        if (!this.connections.has(conversationId)) {
            this.connections.set(conversationId, this.createConnection(conversationId));
        }
        
        return this.connections.get(conversationId);
    }
}
```

### 3. Message Caching
```javascript
// Cache recent messages locally
class MessageCache {
    constructor(maxSize = 1000) {
        this.cache = new Map();
        this.maxSize = maxSize;
    }

    addMessage(conversationId, message) {
        if (!this.cache.has(conversationId)) {
            this.cache.set(conversationId, []);
        }
        
        const messages = this.cache.get(conversationId);
        messages.unshift(message);
        
        // Keep only recent messages
        if (messages.length > this.maxSize) {
            messages.splice(this.maxSize);
        }
    }
}
```

### 4. Optimistic Updates
```javascript
// Send message optimistically
async sendMessageOptimistic(conversationId, content) {
    const tempId = `temp-${Date.now()}`;
    const tempMessage = {
        id: tempId,
        content,
        sender_id: this.userId,
        created_at: new Date().toISOString(),
        status: 'sending'
    };

    // Add to UI immediately
    this.addMessageToUI(tempMessage);

    try {
        const response = await this.sendMessage(conversationId, content);
        
        // Replace temp message with real one
        this.replaceMessage(tempId, response);
    } catch (error) {
        // Mark as failed
        this.updateMessageStatus(tempId, 'failed');
    }
}
```

## 🔒 Security

### 1. Authentication
- All endpoints require valid JWT tokens
- Tokens are validated with Supabase
- WebSocket connections require authentication

### 2. Authorization
- Users can only access conversations they participate in
- Message editing/deletion restricted to message owner
- Participant management restricted to admins/moderators

### 3. Input Validation
```python
# Message content validation
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="text", regex="^(text|image|file|system)$")
```

### 4. Rate Limiting
- Prevents spam and abuse
- Role-based limits
- Distributed rate limiting with Redis

### 5. File Upload Security
```python
# File validation
ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain']
MAX_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "File type not allowed")
    
    if file.size > MAX_SIZE:
        raise HTTPException(400, "File too large")
```

## 🧪 Testing

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest app/tests/test_messaging.py -v

# Run specific test class
pytest app/tests/test_messaging.py::TestConversationManagement -v

# Run with coverage
pytest app/tests/test_messaging.py --cov=app.routes.messaging --cov-report=html
```

### Test Categories
1. **Unit Tests** - Individual function testing
2. **Integration Tests** - Complete workflow testing
3. **Performance Tests** - Load and stress testing
4. **Security Tests** - Authentication and authorization
5. **WebSocket Tests** - Real-time functionality

### Example Test
```python
@pytest.mark.asyncio
async def test_send_message_flow():
    """Test complete message sending flow"""
    # 1. Create conversation
    conversation = await create_conversation(["user-1", "user-2"])
    
    # 2. Send message
    message = await send_message(conversation["id"], "Hello!")
    
    # 3. Verify message was sent
    assert message["content"] == "Hello!"
    assert message["sender_id"] == "user-1"
    
    # 4. Verify WebSocket notification
    # (This would test the WebSocket broadcasting)
```

## 📈 Monitoring and Analytics

### Key Metrics to Track
1. **Message Volume** - Messages per minute/hour
2. **Active Conversations** - Number of active conversations
3. **User Engagement** - Messages per user
4. **Response Times** - API and WebSocket response times
5. **Error Rates** - Failed requests and WebSocket errors
6. **Rate Limit Hits** - Number of rate limit violations

### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Log message sending
logger.info(f"Message sent: {message_id} by {sender_id} in {conversation_id}")

# Log WebSocket events
logger.info(f"User {user_id} joined conversation {conversation_id}")

# Log errors
logger.error(f"Failed to send message: {error}")
```

## 🚀 Deployment

### Docker Configuration
```dockerfile
# Add to existing Dockerfile
RUN pip install redis

# Environment variables
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
```

### Docker Compose
```yaml
services:
  redis:
    image: redis:7.2
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  ai-tutor-backend:
    # ... existing configuration
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
```

### Production Considerations
1. **Load Balancing** - Use multiple instances behind a load balancer
2. **Redis Clustering** - For high availability
3. **Monitoring** - Implement comprehensive monitoring
4. **Backup** - Regular database backups
5. **SSL/TLS** - Secure WebSocket connections
6. **CDN** - For file storage and delivery

## 📚 Additional Resources

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [Supabase Documentation](https://supabase.com/docs)
- [Redis Documentation](https://redis.io/documentation)
- [WebSocket API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## 🤝 Support

For questions, issues, or contributions:

1. Check the existing documentation
2. Review the test cases for usage examples
3. Open an issue with detailed information
4. Submit pull requests for improvements

---

**Version**: 1.0.0  
**Last Updated**: January 2024  
**Compatibility**: FastAPI 0.115+, Python 3.8+ 