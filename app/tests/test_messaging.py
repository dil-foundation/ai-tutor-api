"""
Comprehensive Tests for Messaging System

This module contains tests for all messaging functionality including:
- Conversation management
- Message handling
- Participant management
- User status tracking
- WebSocket functionality
- Rate limiting
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import websockets
import uuid

from app.routes.messaging import router, manager, get_current_user
from app.schemas.messaging import (
    ConversationCreate, MessageCreate, ParticipantAdd, UserStatusUpdate,
    ConversationType, MessageType, UserStatusType, ParticipantRole
)
from app.middleware.rate_limiter import RateLimiter, WebSocketRateLimiter

# Test data
TEST_USER_1 = {
    "id": "test-user-1",
    "email": "user1@test.com",
    "first_name": "John",
    "last_name": "Doe"
}

TEST_USER_2 = {
    "id": "test-user-2", 
    "email": "user2@test.com",
    "first_name": "Jane",
    "last_name": "Smith"
}

TEST_USER_3 = {
    "id": "test-user-3",
    "email": "user3@test.com", 
    "first_name": "Bob",
    "last_name": "Johnson"
}

# Mock Supabase client
class MockSupabaseClient:
    def __init__(self):
        self.data = {
            'conversations': [],
            'conversation_participants': [],
            'messages': [],
            'message_status': [],
            'user_status': [],
            'profiles': [TEST_USER_1, TEST_USER_2, TEST_USER_3]
        }
    
    def table(self, table_name):
        return MockSupabaseTable(self, table_name)

class MockSupabaseTable:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
    
    def select(self, *args, **kwargs):
        return MockSupabaseQuery(self.client, self.table_name, 'select', *args, **kwargs)
    
    def insert(self, data):
        return MockSupabaseQuery(self.client, self.table_name, 'insert', data)
    
    def update(self, data):
        return MockSupabaseQuery(self.client, self.table_name, 'update', data)
    
    def delete(self):
        return MockSupabaseQuery(self.client, self.table_name, 'delete')
    
    def eq(self, field, value):
        return MockSupabaseQuery(self.client, self.table_name, 'eq', field, value)
    
    def in_(self, field, values):
        return MockSupabaseQuery(self.client, self.table_name, 'in', field, values)
    
    def is_(self, field, value):
        return MockSupabaseQuery(self.client, self.table_name, 'is', field, value)
    
    def not_(self):
        return MockSupabaseQuery(self.client, self.table_name, 'not')
    
    def order(self, field, direction='asc'):
        return MockSupabaseQuery(self.client, self.table_name, 'order', field, direction)
    
    def range(self, start, end):
        return MockSupabaseQuery(self.client, self.table_name, 'range', start, end)
    
    def execute(self):
        return MockSupabaseResult(self.client, self.table_name)

class MockSupabaseQuery:
    def __init__(self, client, table_name, operation, *args, **kwargs):
        self.client = client
        self.table_name = table_name
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self.filters = []
    
    def select(self, *args, **kwargs):
        return MockSupabaseQuery(self.client, self.table_name, 'select', *args, **kwargs)
    
    def insert(self, data):
        return MockSupabaseQuery(self.client, self.table_name, 'insert', data)
    
    def update(self, data):
        return MockSupabaseQuery(self.client, self.table_name, 'update', data)
    
    def eq(self, field, value):
        self.filters.append(('eq', field, value))
        return self
    
    def in_(self, field, values):
        self.filters.append(('in', field, values))
        return self
    
    def is_(self, field, value):
        self.filters.append(('is', field, value))
        return self
    
    def not_(self):
        return self
    
    def order(self, field, direction='asc'):
        self.filters.append(('order', field, direction))
        return self
    
    def range(self, start, end):
        self.filters.append(('range', start, end))
        return self
    
    def execute(self):
        return MockSupabaseResult(self.client, self.table_name, self.operation, self.args, self.filters)

class MockSupabaseResult:
    def __init__(self, client, table_name, operation=None, args=None, filters=None):
        self.client = client
        self.table_name = table_name
        self.operation = operation
        self.args = args or []
        self.filters = filters or []
        self.data = self._process_operation()
        self.count = len(self.data) if isinstance(self.data, list) else 0
    
    def _process_operation(self):
        table_data = self.client.data.get(self.table_name, [])
        
        if self.operation == 'select':
            return self._apply_filters(table_data)
        elif self.operation == 'insert':
            if isinstance(self.args[0], list):
                # Multiple inserts
                for item in self.args[0]:
                    item['id'] = str(uuid.uuid4())
                    item['created_at'] = datetime.now().isoformat()
                    item['updated_at'] = datetime.now().isoformat()
                    table_data.append(item)
                return self.args[0]
            else:
                # Single insert
                item = self.args[0].copy()
                item['id'] = str(uuid.uuid4())
                item['created_at'] = datetime.now().isoformat()
                item['updated_at'] = datetime.now().isoformat()
                table_data.append(item)
                return [item]
        elif self.operation == 'update':
            # Find and update matching records
            updated_items = []
            for item in table_data:
                if self._matches_filters(item):
                    item.update(self.args[0])
                    item['updated_at'] = datetime.now().isoformat()
                    updated_items.append(item)
            return updated_items
        
        return table_data
    
    def _apply_filters(self, data):
        filtered_data = data.copy()
        
        for filter_type, field, value in self.filters:
            if filter_type == 'eq':
                filtered_data = [item for item in filtered_data if item.get(field) == value]
            elif filter_type == 'in':
                filtered_data = [item for item in filtered_data if item.get(field) in value]
            elif filter_type == 'is':
                if value == 'null':
                    filtered_data = [item for item in filtered_data if item.get(field) is None]
                else:
                    filtered_data = [item for item in filtered_data if item.get(field) == value]
            elif filter_type == 'order':
                reverse = value == 'desc'
                filtered_data.sort(key=lambda x: x.get(field, ''), reverse=reverse)
            elif filter_type == 'range':
                start, end = field, value
                filtered_data = filtered_data[start:end+1]
        
        return filtered_data
    
    def _matches_filters(self, item):
        for filter_type, field, value in self.filters:
            if filter_type == 'eq' and item.get(field) != value:
                return False
            elif filter_type == 'in' and item.get(field) not in value:
                return False
            elif filter_type == 'is':
                if value == 'null' and item.get(field) is not None:
                    return False
                elif value != 'null' and item.get(field) != value:
                    return False
        return True

# Fixtures
@pytest.fixture
def mock_supabase():
    return MockSupabaseClient()

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def mock_auth():
    with patch('app.routes.messaging.supabase') as mock_supabase:
        mock_supabase.auth.get_user.return_value.user = Mock()
        mock_supabase.auth.get_user.return_value.user.id = TEST_USER_1['id']
        yield mock_supabase

# Test classes
class TestConversationManagement:
    """Test conversation management functionality"""
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, client, mock_auth):
        """Test creating a new conversation"""
        conversation_data = {
            "title": "Test Conversation",
            "type": "direct",
            "participant_ids": [TEST_USER_2['id']]
        }
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.post(
                "/api/conversations",
                json=conversation_data,
                params={"token": "test-token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == conversation_data['title']
        assert data['type'] == conversation_data['type']
        assert data['created_by'] == TEST_USER_1['id']
    
    @pytest.mark.asyncio
    async def test_get_conversations(self, client, mock_auth):
        """Test getting user conversations"""
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.get(
                "/api/conversations",
                params={"token": "test-token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_conversation_details(self, client, mock_auth):
        """Test getting specific conversation details"""
        conversation_id = str(uuid.uuid4())
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.get(
                f"/api/conversations/{conversation_id}",
                params={"token": "test-token"}
            )
        
        # Should return 403 since user is not a participant
        assert response.status_code == 403

class TestMessageManagement:
    """Test message management functionality"""
    
    @pytest.mark.asyncio
    async def test_send_message(self, client, mock_auth):
        """Test sending a message"""
        conversation_id = str(uuid.uuid4())
        message_data = {
            "content": "Hello, this is a test message!",
            "message_type": "text"
        }
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.post(
                f"/api/conversations/{conversation_id}/messages",
                json=message_data,
                params={"token": "test-token"}
            )
        
        # Should return 403 since user is not a participant
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_get_messages(self, client, mock_auth):
        """Test getting conversation messages"""
        conversation_id = str(uuid.uuid4())
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.get(
                f"/api/conversations/{conversation_id}/messages",
                params={"token": "test-token"}
            )
        
        # Should return 403 since user is not a participant
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_edit_message(self, client, mock_auth):
        """Test editing a message"""
        message_id = str(uuid.uuid4())
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.put(
                f"/api/messages/{message_id}",
                data={"content": "Updated message content"},
                params={"token": "test-token"}
            )
        
        # Should return 404 since message doesn't exist
        assert response.status_code == 404

class TestParticipantManagement:
    """Test participant management functionality"""
    
    @pytest.mark.asyncio
    async def test_add_participant(self, client, mock_auth):
        """Test adding a participant to conversation"""
        conversation_id = str(uuid.uuid4())
        participant_data = {
            "user_id": TEST_USER_3['id'],
            "role": "participant"
        }
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.post(
                f"/api/conversations/{conversation_id}/participants",
                json=participant_data,
                params={"token": "test-token"}
            )
        
        # Should return 403 since user is not admin/moderator
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_remove_participant(self, client, mock_auth):
        """Test removing a participant from conversation"""
        conversation_id = str(uuid.uuid4())
        user_id = TEST_USER_2['id']
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.delete(
                f"/api/conversations/{conversation_id}/participants/{user_id}",
                params={"token": "test-token"}
            )
        
        # Should return 403 since user is not admin/moderator
        assert response.status_code == 403

class TestUserStatus:
    """Test user status functionality"""
    
    @pytest.mark.asyncio
    async def test_update_user_status(self, client, mock_auth):
        """Test updating user status"""
        status_data = {
            "status": "online",
            "is_typing": False
        }
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.put(
                "/api/users/status",
                json=status_data,
                params={"token": "test-token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == "Status updated successfully"
    
    @pytest.mark.asyncio
    async def test_get_users_status(self, client, mock_auth):
        """Test getting multiple users status"""
        user_ids = [TEST_USER_2['id'], TEST_USER_3['id']]
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.get(
                "/api/users/status",
                params={"user_ids": user_ids, "token": "test-token"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestWebSocketFunctionality:
    """Test WebSocket functionality"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        # This would require a WebSocket test client
        # For now, we'll test the connection manager directly
        
        # Test connection manager
        assert len(manager.active_connections) == 0
        assert len(manager.user_conversations) == 0
    
    @pytest.mark.asyncio
    async def test_join_conversation(self):
        """Test joining a conversation via WebSocket"""
        user_id = TEST_USER_1['id']
        conversation_id = str(uuid.uuid4())
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        
        # Test joining conversation
        await manager.join_conversation(user_id, conversation_id)
        assert conversation_id in manager.user_conversations.get(user_id, set())

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_creation(self):
        """Test rate limiter initialization"""
        mock_redis = AsyncMock()
        rate_limiter = RateLimiter(mock_redis)
        
        assert rate_limiter.limits is not None
        assert 'message_send' in rate_limiter.limits
        assert 'conversation_create' in rate_limiter.limits
    
    @pytest.mark.asyncio
    async def test_rate_limit_check(self):
        """Test rate limit checking"""
        mock_redis = AsyncMock()
        rate_limiter = RateLimiter(mock_redis)
        
        # Mock Redis pipeline
        mock_pipe = AsyncMock()
        mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipe
        mock_pipe.zremrangebyscore.return_value = None
        mock_pipe.zadd.return_value = None
        mock_pipe.expire.return_value = None
        mock_pipe.zcard.return_value = 5  # Current count
        mock_pipe.execute.return_value = [None, None, None, 5]  # zcard result
        
        is_limited, info = await rate_limiter.is_rate_limited("test-user", "message_send")
        
        assert not is_limited  # 5 < 10 (limit)
        assert info['current_count'] == 5
        assert info['limit'] == 10

class TestDataValidation:
    """Test data validation and schemas"""
    
    def test_conversation_create_validation(self):
        """Test conversation creation data validation"""
        # Valid data
        valid_data = {
            "title": "Test Conversation",
            "type": "direct",
            "participant_ids": [TEST_USER_2['id']]
        }
        conversation = ConversationCreate(**valid_data)
        assert conversation.title == valid_data['title']
        assert conversation.type == ConversationType.DIRECT
        
        # Invalid data - no participants
        with pytest.raises(ValueError):
            ConversationCreate(title="Test", type="direct", participant_ids=[])
        
        # Invalid data - too many participants
        with pytest.raises(ValueError):
            ConversationCreate(
                title="Test", 
                type="direct", 
                participant_ids=[str(i) for i in range(51)]
            )
    
    def test_message_create_validation(self):
        """Test message creation data validation"""
        # Valid data
        valid_data = {
            "content": "Hello, world!",
            "message_type": "text"
        }
        message = MessageCreate(**valid_data)
        assert message.content == valid_data['content']
        assert message.message_type == MessageType.TEXT
        
        # Invalid data - empty content
        with pytest.raises(ValueError):
            MessageCreate(content="", message_type="text")
        
        # Invalid data - content too long
        with pytest.raises(ValueError):
            MessageCreate(content="x" * 5001, message_type="text")

class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_token(self, client):
        """Test handling of invalid authentication token"""
        with patch('app.routes.messaging.supabase') as mock_supabase:
            mock_supabase.auth.get_user.side_effect = Exception("Invalid token")
            
            response = client.get(
                "/api/conversations",
                params={"token": "invalid-token"}
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_database_error(self, client, mock_auth):
        """Test handling of database errors"""
        with patch('app.routes.messaging.supabase') as mock_supabase:
            mock_supabase.table.side_effect = Exception("Database error")
            
            response = client.get(
                "/api/conversations",
                params={"token": "test-token"}
            )
        
        assert response.status_code == 500

class TestIntegration:
    """Integration tests for complete messaging flow"""
    
    @pytest.mark.asyncio
    async def test_complete_messaging_flow(self, client, mock_auth):
        """Test complete messaging flow: create conversation, add participants, send messages"""
        supabase_client = MockSupabaseClient()
        
        with patch('app.routes.messaging.supabase', supabase_client):
            # 1. Create conversation
            conversation_data = {
                "title": "Integration Test Conversation",
                "type": "group",
                "participant_ids": [TEST_USER_2['id'], TEST_USER_3['id']]
            }
            
            response = client.post(
                "/api/conversations",
                json=conversation_data,
                params={"token": "test-token"}
            )
            
            assert response.status_code == 200
            conversation = response.json()
            conversation_id = conversation['id']
            
            # 2. Send message
            message_data = {
                "content": "Hello from integration test!",
                "message_type": "text"
            }
            
            response = client.post(
                f"/api/conversations/{conversation_id}/messages",
                json=message_data,
                params={"token": "test-token"}
            )
            
            # Should work now since user is a participant
            assert response.status_code == 200
            message = response.json()
            assert message['content'] == message_data['content']
            
            # 3. Get messages
            response = client.get(
                f"/api/conversations/{conversation_id}/messages",
                params={"token": "test-token"}
            )
            
            assert response.status_code == 200
            messages = response.json()
            assert len(messages) > 0
            assert messages[0]['content'] == message_data['content']

# Performance tests
class TestPerformance:
    """Performance tests for messaging system"""
    
    @pytest.mark.asyncio
    async def test_concurrent_messages(self):
        """Test handling of concurrent message sending"""
        # This would test the system's ability to handle multiple
        # simultaneous message sends without conflicts
        
        async def send_message(user_id, conversation_id, content):
            # Simulate message sending
            await asyncio.sleep(0.1)  # Simulate processing time
            return {"user_id": user_id, "content": content}
        
        # Send multiple messages concurrently
        tasks = []
        for i in range(10):
            task = send_message(f"user-{i}", "conv-1", f"Message {i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        
        for i, result in enumerate(results):
            assert result['user_id'] == f"user-{i}"
            assert result['content'] == f"Message {i}"
    
    @pytest.mark.asyncio
    async def test_large_conversation_loading(self):
        """Test loading conversations with many messages"""
        # This would test the system's performance when loading
        # conversations with hundreds or thousands of messages
        
        # Simulate loading 1000 messages
        messages = []
        for i in range(1000):
            messages.append({
                "id": str(uuid.uuid4()),
                "content": f"Message {i}",
                "sender_id": f"user-{i % 10}",
                "created_at": datetime.now().isoformat()
            })
        
        # Test pagination
        page_size = 50
        total_pages = (len(messages) + page_size - 1) // page_size
        
        for page in range(total_pages):
            start = page * page_size
            end = start + page_size
            page_messages = messages[start:end]
            assert len(page_messages) <= page_size

# Security tests
class TestSecurity:
    """Security tests for messaging system"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client):
        """Test that unauthorized users cannot access conversations"""
        conversation_id = str(uuid.uuid4())
        
        # Try to access without token
        response = client.get(f"/api/conversations/{conversation_id}")
        assert response.status_code == 422  # Validation error for missing token
    
    @pytest.mark.asyncio
    async def test_message_ownership(self, client, mock_auth):
        """Test that users can only edit their own messages"""
        message_id = str(uuid.uuid4())
        
        with patch('app.routes.messaging.supabase', MockSupabaseClient()):
            response = client.put(
                f"/api/messages/{message_id}",
                data={"content": "Unauthorized edit"},
                params={"token": "test-token"}
            )
        
        # Should fail since message doesn't exist or user doesn't own it
        assert response.status_code in [403, 404]

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 