# Message Read Status API and WebSocket Events Implementation

## Overview

This implementation adds comprehensive message read status tracking to the messaging system, including:

1. **Mark Conversation as Read API** - `POST /api/conversations/{conversation_id}/read`
2. **Accurate Unread Count Calculation** - Updated `GET /api/conversations` endpoint
3. **WebSocket Event Broadcasting** - Real-time read status notifications
4. **Proper Message Status Creation** - Enhanced `send_message` endpoint

## New API Endpoint

### POST /api/conversations/{conversation_id}/read

**Purpose**: Mark all messages in a conversation as read for the current user

**Authentication**: Required (Bearer token)

**Request**:
```http
POST /api/conversations/{conversation_id}/read
Authorization: Bearer {token}
```

**Response**:
```json
{
  "message": "Conversation marked as read"
}
```

**Behavior**:
1. Validates user is a participant in the conversation
2. Updates `conversation_participants.last_read_at` for the current user
3. Updates all `message_status.status` to 'read' for the current user in this conversation
4. Broadcasts WebSocket event to notify other participants

## Enhanced Features

### 1. Accurate Unread Count Calculation

The `GET /api/conversations` endpoint now calculates unread counts correctly:

- **Excludes messages sent by the current user** from unread count
- **Counts only messages with status 'sent'** in the specific conversation
- **Uses proper database joins** between `message_status` and `messages` tables

**SQL Logic**:
```sql
-- Get unread message IDs for current user
SELECT message_id FROM message_status 
WHERE user_id = $1 AND status = 'sent'

-- Count unread messages in specific conversation (excluding sender's own messages)
SELECT COUNT(*) FROM messages 
WHERE id IN (unread_message_ids) 
  AND conversation_id = $2 
  AND sender_id != $1 
  AND is_deleted = false
```

### 2. WebSocket Event Broadcasting

When a conversation is marked as read, a WebSocket event is broadcast to all participants:

**Event Type**: `message_read`

**Payload**:
```json
{
  "type": "message_read",
  "conversation_id": "conversation-id",
  "user_id": "user-id",
  "timestamp": "2025-08-02T00:30:00Z"
}
```

**Frontend Handling**:
```javascript
// Frontend should listen for this event and update UI accordingly
socket.on('message_read', (data) => {
  // Update unread counts
  // Update message status indicators
  // Show read receipts if needed
});
```

### 3. Enhanced Message Status Creation

The `send_message` endpoint now creates proper message status records:

- **Sender**: Gets `status = 'read'` (immediately read)
- **Other participants**: Get `status = 'sent'` (unread until they mark as read)

**Before**:
```python
# Only created status for other participants
if participant['user_id'] != current_user.id:
    status_entries.append({
        'message_id': message_id,
        'user_id': participant['user_id'],
        'status': 'sent'
    })
```

**After**:
```python
# Creates status for all participants with appropriate status
status = 'read' if participant['user_id'] == current_user.id else 'sent'
status_entries.append({
    'message_id': message_id,
    'user_id': participant['user_id'],
    'status': status
})
```

## Database Schema Requirements

### message_status Table
```sql
CREATE TABLE message_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('sent', 'read')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(message_id, user_id)
);
```

### conversation_participants Table
```sql
CREATE TABLE conversation_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'participant',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    left_at TIMESTAMP WITH TIME ZONE,
    last_read_at TIMESTAMP WITH TIME ZONE,
    is_muted BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    UNIQUE(conversation_id, user_id)
);
```

## Frontend Integration

### 1. Mark Conversation as Read
```javascript
// Call when user opens a conversation
async function markConversationAsRead(conversationId) {
  try {
    const response = await fetch(`/api/conversations/${conversationId}/read`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      console.log('Conversation marked as read');
    }
  } catch (error) {
    console.error('Error marking conversation as read:', error);
  }
}
```

### 2. Handle Read Status Events
```javascript
// WebSocket event handler
socket.on('message_read', (data) => {
  const { conversation_id, user_id, timestamp } = data;
  
  // Update UI to show messages as read
  updateMessageReadStatus(conversation_id, user_id, timestamp);
  
  // Update unread count in conversation list
  updateConversationUnreadCount(conversation_id, 0);
});
```

### 3. Display Unread Counts
```javascript
// The unread_count is now included in conversation objects
conversations.forEach(conversation => {
  if (conversation.unread_count > 0) {
    showUnreadBadge(conversation.id, conversation.unread_count);
  }
});
```

## Testing

Use the provided test script `test_message_read_status.py` to verify the implementation:

```bash
python test_message_read_status.py
```

**Test Coverage**:
1. ✅ Mark conversation as read API
2. ✅ Unread count calculation
3. ✅ Message status creation
4. ✅ WebSocket event broadcasting

## Logging

The implementation includes comprehensive logging for debugging:

- `📖 [MARK_READ]` - Read status operations
- `📡 [MARK_READ]` - WebSocket broadcasting
- `📝 [SEND_MESSAGE]` - Message status creation
- `📋 [CONVERSATIONS]` - Unread count calculations

## Error Handling

- **403 Forbidden**: User not a participant in conversation
- **404 Not Found**: Conversation doesn't exist
- **500 Internal Server Error**: Database or WebSocket errors

WebSocket broadcasting failures don't fail the main request - they're logged but don't prevent the read status from being updated.

## Performance Considerations

1. **Batch Updates**: Message status updates are done in a loop (could be optimized with batch operations)
2. **Indexing**: Ensure proper indexes on `message_status(user_id, status)` and `messages(conversation_id, sender_id)`
3. **Caching**: Consider caching unread counts for frequently accessed conversations

## Future Enhancements

1. **Read Receipts**: Show who has read specific messages
2. **Typing Indicators**: Real-time typing status
3. **Message Reactions**: Like, heart, etc. reactions
4. **Message Threading**: Reply to specific messages
5. **Message Search**: Search within conversations 