# AI English Tutor API - Technical Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Key Components](#key-components)
4. [Database Design](#database-design)
5. [API Endpoints](#api-endpoints)
6. [WebSocket Flows](#websocket-flows)
7. [Sequence Diagrams](#sequence-diagrams)
8. [Security & Authentication](#security--authentication)
9. [External Integrations](#external-integrations)
10. [Deployment](#deployment)

## System Overview

The AI English Tutor API is a comprehensive FastAPI-based backend system designed to provide personalized English learning experiences for Urdu-speaking learners. The system features real-time conversation practice, progress tracking, messaging capabilities, and multi-stage learning exercises.

### Key Features
- **Multi-Stage Learning System**: 6 stages from A1 Beginner to C2 Mastery
- **Real-time Conversation Practice**: WebSocket-based voice interactions
- **Progress Tracking**: Comprehensive analytics and achievement system
- **Messaging System**: Real-time chat with WebSocket support
- **AI-Powered Feedback**: GPT-4 based evaluation and correction
- **Multi-modal Support**: Speech-to-Text, Text-to-Speech, Translation
- **Authentication & Authorization**: JWT-based with role management

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Frontend]
        MOBILE[Mobile App]
    end
    
    subgraph "API Gateway"
        FASTAPI[FastAPI Application]
        CORS[CORS Middleware]
        AUTH[Auth Middleware]
    end
    
    subgraph "Business Logic"
        ROUTES[Route Handlers]
        SERVICES[Service Layer]
        MIDDLEWARE[Custom Middleware]
    end
    
    subgraph "External Services"
        OPENAI[OpenAI GPT-4]
        ELEVEN[ElevenLabs STT/TTS]
        GOOGLE[Google Cloud STT]
    end
    
    subgraph "Data Layer"
        SUPABASE[(Supabase PostgreSQL)]
        MYSQL[(MySQL Database)]
        REDIS[(Redis Cache)]
    end
    
    WEB --> FASTAPI
    MOBILE --> FASTAPI
    FASTAPI --> CORS
    CORS --> AUTH
    AUTH --> ROUTES
    ROUTES --> SERVICES
    SERVICES --> OPENAI
    SERVICES --> ELEVEN
    SERVICES --> GOOGLE
    SERVICES --> SUPABASE
    SERVICES --> MYSQL
    SERVICES --> REDIS
```

### Component Architecture

```mermaid
graph LR
    subgraph "FastAPI Application"
        MAIN[main.py]
        CONFIG[config.py]
        
        subgraph "Routes"
            USER_R[user.py]
            MSG_R[messaging.py]
            PROG_R[progress_tracking.py]
            CONV_R[conversation_ws.py]
            ENG_R[english_only_ws.py]
            EXERCISES[Exercise Routes]
        end
        
        subgraph "Services"
            TTS[tts.py]
            STT[stt.py]
            TRANS[translation.py]
            FEEDBACK[feedback.py]
            EVAL[evaluator.py]
        end
        
        subgraph "Middleware"
            AUTH_M[auth_middleware.py]
            RATE[rate_limiter.py]
        end
        
        subgraph "Database"
            DB[database.py]
            SUPABASE_CLIENT[supabase_client.py]
            REDIS_CLIENT[redis_client.py]
        end
    end
    
    MAIN --> USER_R
    MAIN --> MSG_R
    MAIN --> PROG_R
    USER_R --> AUTH_M
    MSG_R --> SUPABASE_CLIENT
    PROG_R --> SUPABASE_CLIENT
    CONV_R --> TTS
    CONV_R --> STT
    ENG_R --> FEEDBACK
    SERVICES --> DB
```

## Key Components

### 1. Main Application (`main.py`)
- **Purpose**: Application entry point and router configuration
- **Features**: 
  - FastAPI app initialization with comprehensive metadata
  - CORS configuration for cross-origin requests
  - Route inclusion with organized tagging system
  - Startup/shutdown event handlers
  - Health check endpoints

### 2. Authentication System (`auth_middleware.py`)
- **Purpose**: JWT-based authentication and authorization
- **Features**:
  - Supabase JWT token validation
  - Role-based access control (admin, teacher, student)
  - User session management
  - Protected route decorators

### 3. Progress Tracking System (`supabase_client.py`)
- **Purpose**: Comprehensive learning progress management
- **Features**:
  - User progress initialization
  - Topic attempt recording
  - Exercise and stage completion tracking
  - Achievement system
  - Streak calculation
  - Content unlocking logic

### 4. Messaging System (`routes/messaging.py`)
- **Purpose**: Real-time messaging and conversation management
- **Features**:
  - Conversation CRUD operations
  - Real-time message delivery via WebSocket
  - Message status tracking (sent, delivered, read)
  - Participant management
  - File upload support
  - Typing indicators

### 5. AI Services
#### Speech-to-Text (`services/stt.py`)
- **ElevenLabs STT**: Primary STT service with language detection
- **Google Cloud STT**: Fallback STT service
- **Features**: Multi-language support, audio format conversion, noise filtering

#### Text-to-Speech (`services/tts.py`)
- **ElevenLabs TTS**: High-quality voice synthesis
- **Features**: Multiple voice settings, speed control, audio caching

#### Translation (`services/translation.py`)
- **OpenAI GPT-4**: Urdu ↔ English translation
- **Features**: Context-aware translation, grammar correction

#### Feedback System (`services/feedback.py`)
- **OpenAI GPT-4**: AI-powered conversation analysis
- **Features**: Multi-stage conversation management, error correction, learning path adaptation

## Database Design

### Primary Databases

#### 1. Supabase PostgreSQL (Progress & Messaging)
```sql
-- User Progress Tables
ai_tutor_user_progress_summary
ai_tutor_user_stage_progress
ai_tutor_user_exercise_progress
ai_tutor_user_topic_progress
ai_tutor_daily_learning_analytics
ai_tutor_learning_unlocks

-- Messaging Tables
conversations
messages
conversation_participants
message_status
user_status
profiles
```

#### 2. MySQL (WordPress Integration)
```sql
-- WordPress Tables
wp_users
wp_usermeta
```

#### 3. Redis (Caching)
- Session caching
- TTS audio caching
- Translation caching
- Rate limiting

### Data Models

#### Progress Tracking Schema
```mermaid
erDiagram
    USER_PROGRESS_SUMMARY {
        string user_id PK
        int current_stage
        int current_exercise
        int topic_id
        boolean urdu_enabled
        json unlocked_stages
        json unlocked_exercises
        float overall_progress_percentage
        int total_time_spent_minutes
        int total_exercises_completed
        int streak_days
        int longest_streak
        datetime first_activity_date
        datetime last_activity_date
    }
    
    USER_STAGE_PROGRESS {
        string user_id PK
        int stage_id PK
        datetime started_at
        datetime completed_at
        float average_score
        int total_attempts
    }
    
    USER_EXERCISE_PROGRESS {
        string user_id PK
        int stage_id PK
        int exercise_id PK
        int current_topic_id
        int attempts
        json scores
        json last_5_scores
        float average_score
        json urdu_used
        int time_spent_minutes
        float best_score
        boolean mature
        datetime started_at
        datetime completed_at
    }
    
    USER_TOPIC_PROGRESS {
        string user_id PK
        int stage_id PK
        int exercise_id PK
        int topic_id PK
        int attempt_num
        float score
        boolean urdu_used
        boolean completed
        int total_time_seconds
    }
    
    USER_PROGRESS_SUMMARY ||--o{ USER_STAGE_PROGRESS : has
    USER_STAGE_PROGRESS ||--o{ USER_EXERCISE_PROGRESS : contains
    USER_EXERCISE_PROGRESS ||--o{ USER_TOPIC_PROGRESS : includes
```

#### Messaging Schema
```mermaid
erDiagram
    CONVERSATIONS {
        uuid id PK
        string title
        string type
        uuid created_by FK
        datetime created_at
        datetime updated_at
        datetime last_message_at
        boolean is_archived
        boolean is_deleted
    }
    
    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        uuid sender_id FK
        string content
        string message_type
        uuid reply_to_id FK
        json metadata
        datetime created_at
        datetime updated_at
        boolean is_edited
        boolean is_deleted
    }
    
    CONVERSATION_PARTICIPANTS {
        uuid id PK
        uuid conversation_id FK
        uuid user_id FK
        string role
        datetime joined_at
        datetime left_at
        boolean is_muted
        boolean is_blocked
        datetime last_read_at
    }
    
    MESSAGE_STATUS {
        uuid id PK
        uuid message_id FK
        uuid user_id FK
        string status
        datetime created_at
        datetime updated_at
    }
    
    CONVERSATIONS ||--o{ MESSAGES : contains
    CONVERSATIONS ||--o{ CONVERSATION_PARTICIPANTS : has
    MESSAGES ||--o{ MESSAGE_STATUS : tracks
```

## API Endpoints

### Authentication Endpoints
```
POST /user/register                    # User registration with CEFR evaluation
POST /user/register-wordpress          # WordPress user creation
POST /user/login-wordpress             # WordPress user authentication
```

### Progress Tracking Endpoints
```
POST /api/progress/initialize-progress      # Initialize user progress
POST /api/progress/record-topic-attempt     # Record learning attempt
GET  /api/progress/user-progress/{user_id}  # Get user progress
POST /api/progress/check-unlocks/{user_id}  # Check content unlocks
POST /api/progress/get-current-topic        # Get current topic for exercise
POST /api/progress/comprehensive-progress   # Get detailed progress data
```

### Messaging Endpoints
```
# Conversations
POST   /api/conversations                    # Create conversation
GET    /api/conversations                    # List conversations (paginated)
GET    /api/conversations/{id}               # Get conversation details
PUT    /api/conversations/{id}               # Update conversation
DELETE /api/conversations/{id}               # Delete conversation

# Messages
POST   /api/conversations/{id}/messages      # Send message
GET    /api/conversations/{id}/messages      # Get messages (paginated)
PUT    /api/messages/{id}                    # Edit message
DELETE /api/messages/{id}                    # Delete message
POST   /api/messages/{id}/read               # Mark message as read
POST   /api/conversations/{id}/read          # Mark conversation as read

# Participants
POST   /api/conversations/{id}/participants  # Add participant
DELETE /api/conversations/{id}/participants/{user_id}  # Remove participant
PUT    /api/conversations/{id}/participants/{user_id}  # Update participant

# User Status
GET    /api/users/status                     # Get user statuses
PUT    /api/users/status                     # Update user status

# File Upload
POST   /api/conversations/{id}/upload        # Upload file to conversation
```

### Learning Exercise Endpoints
```
# Stage 1 - A1 Beginner
/api/repeat-after-me/*          # Exercise 1: Repeat After Me
/api/quick-response/*           # Exercise 2: Quick Response
/api/listen-and-reply/*         # Exercise 3: Listen and Reply

# Stage 2 - A2 Elementary  
/api/daily-routine/*            # Exercise 1: Daily Routine
/api/quick-answer/*             # Exercise 2: Quick Answer
/api/roleplay-simulation/*      # Exercise 3: Roleplay Simulation

# Stage 3 - B1 Intermediate
/api/storytelling/*             # Exercise 1: Storytelling
/api/group-dialogue/*           # Exercise 2: Group Dialogue
/api/problem-solving/*          # Exercise 3: Problem-Solving

# Stage 4 - B2 Upper Intermediate
/api/abstract-topic/*           # Exercise 1: Abstract Topic
/api/mock-interview/*           # Exercise 2: Mock Interview
/api/news-summary/*             # Exercise 3: News Summary

# Stage 5 - C1 Advanced
/api/critical-thinking/*        # Exercise 1: Critical Thinking
/api/academic-presentation/*    # Exercise 2: Academic Presentation
/api/in-depth-interview/*       # Exercise 3: In-Depth Interview

# Stage 6 - C2 Mastery
/api/spontaneous-speech/*       # Exercise 1: Spontaneous Speech
/api/sensitive-scenario/*       # Exercise 2: Sensitive Scenario
/api/critical-opinion-builder/* # Exercise 3: Critical Opinion Builder
```

### WebSocket Endpoints
```
/api/ws/learn                   # Learning conversation WebSocket
/api/ws/english-only           # English-only AI tutor WebSocket
/api/ws/{token}                # Messaging WebSocket with authentication
```

## WebSocket Flows

### 1. Learning Conversation WebSocket (`/api/ws/learn`)

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant STT as STT Service
    participant Translation
    participant TTS as TTS Service
    participant Feedback
    
    Client->>WebSocket: Connect & send audio (base64)
    WebSocket->>STT: Transcribe audio (Urdu)
    STT-->>WebSocket: Transcription result
    
    alt If English detected
        WebSocket->>TTS: Generate "Please speak Urdu" audio
        TTS-->>WebSocket: Audio response
        WebSocket->>Client: Send feedback + audio
    else Urdu detected
        WebSocket->>Translation: Translate Urdu to English
        Translation-->>WebSocket: English translation
        WebSocket->>TTS: Generate "You said" audio
        TTS-->>WebSocket: Audio response
        WebSocket->>Client: Send translation + audio
        
        Client->>WebSocket: "you_said_complete" signal
        WebSocket->>Client: Send word-by-word practice
        Client->>WebSocket: "word_by_word_complete" signal
        WebSocket->>TTS: Generate full sentence audio
        TTS-->>WebSocket: Audio response
        WebSocket->>Client: Send full sentence + audio
        
        loop User Practice Loop
            Client->>WebSocket: User repeat attempt (audio)
            WebSocket->>STT: Transcribe user attempt
            STT-->>WebSocket: User transcription
            WebSocket->>Feedback: Evaluate pronunciation
            Feedback-->>WebSocket: Feedback result
            
            alt If correct
                WebSocket->>TTS: Generate success audio
                TTS-->>WebSocket: Success audio
                WebSocket->>Client: Success feedback + audio
                Note over Client,WebSocket: Exit loop, await next sentence
            else If incorrect
                WebSocket->>TTS: Generate correction audio
                TTS-->>WebSocket: Correction audio
                WebSocket->>Client: Correction feedback + audio
                WebSocket->>Client: Repeat word-by-word practice
                Note over Client,WebSocket: Continue loop
            end
        end
    end
```

### 2. English-Only AI Tutor WebSocket (`/api/ws/english-only`)

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant STT as STT Service
    participant AI as GPT-4 Analysis
    participant TTS as TTS Service
    
    Client->>WebSocket: Connect
    WebSocket->>Client: Greeting message + audio
    
    loop Conversation Loop
        Client->>WebSocket: Send audio message
        WebSocket->>STT: Transcribe audio (English)
        STT-->>WebSocket: English transcription
        
        WebSocket->>AI: Analyze input with conversation stage
        Note over AI: Multi-stage analysis:<br/>- Intent detection<br/>- Vocabulary learning<br/>- Sentence practice<br/>- Topic discussion<br/>- Grammar focus
        AI-->>WebSocket: Analysis result + next stage
        
        WebSocket->>TTS: Generate AI response (slow TTS)
        TTS-->>WebSocket: AI response audio
        WebSocket->>Client: Send response + audio + analysis
        
        Note over WebSocket: Update conversation state:<br/>- Stage transition<br/>- Topic extraction<br/>- Learning path<br/>- Skill assessment
    end
```

### 3. Messaging WebSocket (`/api/ws/{token}`)

```mermaid
sequenceDiagram
    participant Client
    participant WebSocket
    participant Auth as Auth Service
    participant DB as Supabase
    participant Manager as Connection Manager
    
    Client->>WebSocket: Connect with JWT token
    WebSocket->>Auth: Verify JWT token
    Auth-->>WebSocket: User authentication result
    
    alt If authenticated
        WebSocket->>Manager: Register connection
        WebSocket->>DB: Get user conversations
        DB-->>WebSocket: User conversation list
        WebSocket->>Manager: Auto-join conversations
        WebSocket->>Client: Connection established + conversations
        
        loop Message Handling
            Client->>WebSocket: Send message type
            
            alt join_conversation
                WebSocket->>DB: Verify participant status
                WebSocket->>Manager: Join conversation room
                WebSocket->>Client: Joined confirmation
                
            else send_message (via REST API)
                Note over Client: Messages sent via REST API<br/>WebSocket receives broadcasts
                
            else typing_start/stop
                WebSocket->>Manager: Update typing status
                Manager->>WebSocket: Broadcast to conversation
                
            else message_delivered/read
                WebSocket->>DB: Update message status
                WebSocket->>Manager: Broadcast status update
                
            else user_status_change
                WebSocket->>DB: Update user status
                WebSocket->>Manager: Broadcast status change
            end
        end
        
    else Authentication failed
        WebSocket->>Client: Close connection
    end
```

## Sequence Diagrams

### 1. User Registration & Progress Initialization

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant CEFR as CEFR Evaluator
    participant WordPress
    participant Supabase
    participant Progress as Progress Tracker
    
    Client->>API: POST /user/register-wordpress
    API->>WordPress: Create user account
    WordPress-->>API: User created (ID)
    API->>WordPress: Add custom metadata
    WordPress-->>API: Metadata saved
    API->>WordPress: Get JWT token
    WordPress-->>API: JWT token
    API-->>Client: Registration success + token
    
    Client->>API: POST /api/progress/initialize-progress
    API->>Progress: Initialize user progress
    Progress->>Supabase: Create progress summary
    Progress->>Supabase: Create stage 1 progress
    Progress->>Supabase: Create exercise progress (1.1, 1.2, 1.3)
    Progress->>Supabase: Create learning unlocks
    Supabase-->>Progress: All records created
    Progress-->>API: Initialization complete
    API-->>Client: Progress initialized
```

### 2. Learning Session Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Progress as Progress Tracker
    participant STT
    participant Translation
    participant Feedback
    participant TTS
    participant Supabase
    
    Client->>API: GET current topic for exercise
    API->>Progress: Get current topic
    Progress->>Supabase: Query exercise progress
    Supabase-->>Progress: Current topic data
    Progress-->>API: Topic ID
    API-->>Client: Current topic
    
    Client->>API: Start learning session (WebSocket)
    Note over Client,API: WebSocket conversation flow
    
    Client->>API: POST /api/progress/record-topic-attempt
    API->>Progress: Record attempt
    Progress->>Supabase: Update topic progress
    Progress->>Supabase: Update exercise progress
    Progress->>Supabase: Update daily analytics
    Progress->>Supabase: Update user summary
    Progress->>Progress: Calculate streak
    Progress->>Progress: Check content unlocks
    Supabase-->>Progress: All updates complete
    Progress-->>API: Attempt recorded + unlocks
    API-->>Client: Success + unlocked content
```

### 3. Real-time Messaging Flow

```mermaid
sequenceDiagram
    participant Client1
    participant Client2
    participant API
    participant WebSocket1
    participant WebSocket2
    participant Manager as Connection Manager
    participant Supabase
    
    Client1->>API: POST /api/conversations/{id}/messages
    API->>Supabase: Create message
    API->>Supabase: Create message status for all participants
    API->>Supabase: Update conversation last_message_at
    Supabase-->>API: Message created
    
    API->>Manager: Broadcast new message
    Manager->>WebSocket1: Send to sender
    Manager->>WebSocket2: Send to recipient
    WebSocket1->>Client1: New message notification
    WebSocket2->>Client2: New message notification
    
    Client2->>WebSocket2: Mark message as read
    WebSocket2->>Supabase: Update message status
    WebSocket2->>Manager: Broadcast read receipt
    Manager->>WebSocket1: Send read receipt
    WebSocket1->>Client1: Message read notification
```

### 4. Progress Analytics & Achievement Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Progress as Progress Tracker
    participant Supabase
    participant Analytics as Analytics Processor
    
    Client->>API: POST /api/progress/comprehensive-progress
    API->>Progress: Get comprehensive progress
    Progress->>Supabase: Get progress summary
    Progress->>Supabase: Get stage progress
    Progress->>Supabase: Get exercise progress
    Progress->>Supabase: Get learning unlocks
    Supabase-->>Progress: All progress data
    
    Progress->>Analytics: Process progress data
    Analytics->>Analytics: Calculate stage completion
    Analytics->>Analytics: Calculate overall progress
    Analytics->>Analytics: Generate achievements
    Analytics->>Analytics: Calculate fluency trend
    Analytics->>Analytics: Process learning metrics
    Analytics-->>Progress: Processed data
    
    Progress-->>API: Comprehensive progress
    API-->>Client: Detailed progress + achievements
```

## Security & Authentication

### JWT Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Auth as Auth Middleware
    participant Supabase
    
    Client->>API: Request with Authorization header
    API->>Auth: Extract JWT token
    Auth->>Supabase: Verify token
    Supabase-->>Auth: User data + validation
    
    alt Token valid
        Auth->>Auth: Extract user role & permissions
        Auth-->>API: User context
        API->>API: Process request
        API-->>Client: Response
    else Token invalid/expired
        Auth-->>API: 401 Unauthorized
        API-->>Client: Authentication error
    end
```

### Role-Based Access Control

```mermaid
graph TD
    A[Request] --> B{Authenticated?}
    B -->|No| C[401 Unauthorized]
    B -->|Yes| D{Check Role}
    
    D -->|Admin| E[Full Access]
    D -->|Teacher| F{Teacher Resources?}
    D -->|Student| G{Own Data Only?}
    
    F -->|Yes| H[Allow Access]
    F -->|No| I[403 Forbidden]
    
    G -->|Yes| J[Allow Access]
    G -->|No| K[403 Forbidden]
```

### Security Features
- **JWT Token Validation**: Supabase-based token verification
- **Role-Based Authorization**: Admin, Teacher, Student roles
- **Data Isolation**: Users can only access their own progress data
- **Rate Limiting**: Redis-based rate limiting middleware
- **CORS Configuration**: Controlled cross-origin access
- **Input Validation**: Pydantic schema validation
- **SQL Injection Protection**: ORM-based database queries

## External Integrations

### 1. OpenAI GPT-4
- **Purpose**: AI conversation analysis, translation, feedback generation
- **Endpoints**: Chat Completions API
- **Models**: GPT-4 Turbo
- **Usage**: 
  - Urdu ↔ English translation
  - Conversation analysis and feedback
  - Learning path recommendations
  - Error correction and suggestions

### 2. ElevenLabs
- **Purpose**: High-quality speech synthesis and recognition
- **Services**:
  - **Text-to-Speech**: Voice synthesis with emotion control
  - **Speech-to-Text**: Multi-language transcription with noise filtering
- **Features**:
  - Multiple voice settings (stability, similarity, speed)
  - Language detection
  - Audio format conversion
  - Background noise removal

### 3. Google Cloud Speech-to-Text
- **Purpose**: Fallback STT service
- **Features**: Multi-language support, high accuracy
- **Usage**: Backup transcription service

### 4. Supabase
- **Purpose**: Primary database and authentication
- **Services**:
  - **PostgreSQL Database**: Progress tracking, messaging
  - **Authentication**: JWT token management
  - **Real-time**: WebSocket subscriptions (future use)
- **Tables**: 15+ tables for comprehensive data management

### 5. WordPress Integration
- **Purpose**: User management system
- **Features**:
  - User registration and authentication
  - Custom user metadata
  - JWT token generation
- **API**: WordPress REST API v2

### 6. Redis
- **Purpose**: Caching and session management
- **Usage**:
  - TTS audio caching
  - Translation result caching
  - Rate limiting counters
  - Session data storage

## Deployment

### Environment Configuration
```bash
# API Keys
OPENAI_API_KEY=sk-...
ELEVEN_API_KEY=...
ELEVEN_VOICE_ID=...

# Database Configuration
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_NAME=...

# Supabase Configuration
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...

# WordPress Integration
WP_SITE_URL=https://...
WP_API_USERNAME=...
WP_API_APPLICATION_PASSWORD=...

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Application Configuration
ENVIRONMENT=production
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    depends_on:
      - redis
      - mysql
    
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME}
    ports:
      - "3306:3306"
```

### Production Considerations

1. **Scalability**:
   - Horizontal scaling with load balancer
   - Redis cluster for caching
   - Database read replicas

2. **Monitoring**:
   - Application performance monitoring
   - Error tracking and logging
   - Health check endpoints

3. **Security**:
   - HTTPS/TLS encryption
   - Environment variable management
   - Regular security updates

4. **Backup & Recovery**:
   - Database backup strategies
   - Redis persistence configuration
   - Disaster recovery procedures

## Performance Optimizations

### 1. Caching Strategy
- **TTS Audio Caching**: Frequently used audio responses cached in Redis
- **Translation Caching**: Common translations cached with LRU eviction
- **Database Query Optimization**: Indexed queries and connection pooling

### 2. Asynchronous Processing
- **Thread Pool Execution**: CPU-intensive tasks (STT, TTS) run in thread pools
- **Parallel Processing**: Multiple AI service calls executed concurrently
- **WebSocket Optimization**: Non-blocking message handling

### 3. Resource Management
- **Connection Pooling**: HTTP client reuse for external API calls
- **Memory Management**: Limited cache sizes with automatic cleanup
- **Rate Limiting**: Prevents API abuse and ensures fair usage

### 4. Audio Processing Optimization
- **Format Conversion**: Optimized audio format handling with pydub
- **Streaming**: Large audio files processed in chunks
- **Compression**: Audio data compressed for network transmission

## API Rate Limits

| Endpoint Category | Rate Limit | Window |
|------------------|------------|---------|
| Authentication | 10 requests | 1 minute |
| Progress Tracking | 100 requests | 1 hour |
| Messaging | 1000 requests | 1 hour |
| WebSocket Connections | 5 connections | 1 minute |
| File Upload | 20 uploads | 1 hour |

## Error Handling

### HTTP Status Codes
- **200**: Success
- **201**: Created
- **204**: No Content
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (authentication required)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **429**: Too Many Requests (rate limited)
- **500**: Internal Server Error

### Error Response Format
```json
{
  "error": "ValidationError",
  "message": "Invalid input data",
  "details": {
    "field": "email",
    "issue": "Invalid email format"
  },
  "timestamp": "2024-01-20T10:00:00Z"
}
```

## Future Enhancements

1. **Advanced Analytics**: Machine learning-based learning path optimization
2. **Mobile SDK**: Native mobile app integration
3. **Offline Support**: Cached content for offline learning
4. **Gamification**: Enhanced achievement and reward systems
5. **Social Features**: Peer learning and collaboration tools
6. **Multi-language Support**: Additional language pairs beyond Urdu-English
7. **Voice Cloning**: Personalized TTS voices for learners
8. **Real-time Collaboration**: Shared learning sessions and group exercises

---

*This documentation provides a comprehensive overview of the AI English Tutor API system. For specific implementation details, refer to the source code and inline documentation.*
