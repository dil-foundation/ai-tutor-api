# Teacher Dashboard APIs - Comprehensive Documentation

## Overview
This document provides comprehensive documentation for three teacher dashboard APIs, including their implementation, database tables, schemas, and data flow.

---

## API 1: GET /teacher/dashboard/overview

### Endpoint Details

**URL:** `GET /teacher/dashboard/overview`

**Authentication:** Required (Admin or Teacher role)

**Query Parameters:**
- `time_range` (optional, default: "all_time"): Time range filter
  - Options: "today", "this_week", "this_month", "this_year", "all_time"

**Response Model:** `TeacherDashboardResponse`
```json
{
  "success": true,
  "data": {
    "learn_feature_engagement_summary": {
      "total_students_engaged": 150,
      "active_today": 45,
      "total_time_spent_hours": 1250.5,
      "time_period": "all time",
      "avg_responses_per_student": 25,
      "responses_period": "all time",
      "engagement_rate": 75.5,
      "engagement_change": "+5.2%"
    },
    "top_used_practice_lessons": [
      {
        "lesson_name": "Daily Routine Conversations",
        "stage": "Stage 1",
        "access_count": 250,
        "trend": "Up"
      }
    ],
    "last_updated": "2024-01-15T10:30:00"
  },
  "message": "Teacher dashboard data retrieved successfully"
}
```

### Implementation Location
- **File:** `app/routes/teacher_dashboard.py`
- **Endpoint Function:** `get_teacher_dashboard_overview()` (line 155)
- **Helper Functions:**
  - `_get_learn_feature_engagement_summary()` (line 267)
  - `_get_top_used_practice_lessons()` (line 359)

### Features
- **Caching:** Uses Redis cache with 3-minute TTL
- **Parallel Execution:** Uses `asyncio.gather()` for concurrent data fetching
- **Time Range Filtering:** Supports multiple time range options

---

## API 2: GET /teacher/dashboard/behavior-insights

### Endpoint Details

**URL:** `GET /teacher/dashboard/behavior-insights`

**Authentication:** Required (Admin or Teacher role)

**Query Parameters:**
- `time_range` (optional, default: "all_time"): Time range filter

**Response Model:** `TeacherDashboardResponse`
```json
{
  "success": true,
  "data": {
    "high_retry_rate": {
      "has_alert": true,
      "message": "5 students showing excessive retries",
      "affected_students": 5,
      "details": [
        {
          "user_id": "uuid",
          "student_name": "John Doe",
          "total_attempts": 15,
          "stages_affected": [1, 2],
          "topics_affected": 8
        }
      ]
    },
    "low_engagement": {
      "has_alert": false,
      "message": "Engagement is healthy: 75.5%",
      "affected_students": 0
    },
    "inactivity": {
      "has_alert": true,
      "message": "High inactivity detected: 30 inactive students (20%)",
      "affected_students": 30,
      "inactivity_rate": 20.0
    },
    "stuck_students": {
      "has_alert": true,
      "message": "10 students haven't progressed from their current stage in 7+ days",
      "affected_students": 10,
      "details": [...]
    },
    "total_flags": 3
  },
  "message": "Behavior insights retrieved successfully"
}
```

### Implementation Location
- **File:** `app/routes/teacher_dashboard.py`
- **Endpoint Function:** `get_behavior_insights()` (line 661)
- **Helper Function:** `_get_behavior_insights()` (line 930)
- **Sub-Insights:**
  - `_get_high_retry_insight()` (line 968)
  - `_get_low_engagement_insight()` (line 1134)
  - `_get_inactivity_insight()` (line 1202)
  - `_get_stuck_students_insight()` (line 1249)

### Features
- **Caching:** Uses Redis cache with 5-minute TTL
- **Parallel Execution:** All insight calculations run concurrently
- **Alert System:** Flags students with concerning behavior patterns

---

## API 3: GET /teacher/dashboard/progress-overview

### Endpoint Details

**URL:** `GET /teacher/dashboard/progress-overview`

**Authentication:** Required (Admin or Teacher role)

**Query Parameters:**
- `search_query` (optional): Search by student name or email
- `stage_id` (optional): Filter by stage
- `lesson_id` (optional): Filter by lesson
- `time_range` (optional, default: "all_time"): Time range filter

**Response Model:** `TeacherDashboardResponse`
```json
{
  "success": true,
  "data": {
    "students": [
      {
        "user_id": "uuid",
        "student_name": "John Doe",
        "email": "john@example.com",
        "current_stage": "Stage 1: Foundation Speaking",
        "current_lesson": "Daily Routine Conversations",
        "avg_score": 85.5,
        "ai_feedback": "Excellent progress! Keep up the great work.",
        "feedback_sentiment": "positive",
        "last_active": "2024-01-15",
        "progress_percentage": 75.5,
        "is_at_risk": false,
        "total_time_minutes": 1200,
        "exercises_completed": 15
      }
    ],
    "total_students": 150,
    "avg_completion_percentage": 65.5,
    "avg_score": 72.3,
    "students_at_risk_count": 25,
    "filters_applied": {
      "search_query": null,
      "stage_id": null,
      "lesson_id": null,
      "time_range": "all_time"
    }
  },
  "message": "Student progress overview retrieved successfully"
}
```

### Implementation Location
- **File:** `app/routes/teacher_dashboard.py`
- **Endpoint Function:** `get_student_progress_overview()` (line 794)
- **Helper Function:** `_get_student_progress_overview()` (line 1583)

### Features
- **Search Functionality:** Search by student name or email
- **Filtering:** Filter by stage, lesson, and time range
- **AI Feedback:** Generates AI-powered feedback for each student
- **Risk Assessment:** Identifies students at risk (progress < 50% or score < 60)

---

## Database Tables Used

### 1. `ai_tutor_user_progress_summary`
**Purpose:** Main table tracking overall user progress and summary statistics

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_user_progress_summary (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,                    -- User identifier
    current_stage INTEGER DEFAULT 1,                 -- Current stage number (1-6)
    current_exercise INTEGER DEFAULT 1,              -- Current exercise number (1-3)
    topic_id INTEGER DEFAULT 1,                      -- Current topic ID
    unlocked_stages INTEGER[],                       -- Array of unlocked stage IDs
    unlocked_exercises JSONB,                        -- Map of stage_id to exercise_ids array
    overall_progress_percentage NUMERIC,             -- Overall progress (0-100)
    total_exercises_completed INTEGER DEFAULT 0,    -- Total exercises completed
    english_proficiency_text TEXT,                   -- Proficiency level text
    assigned_start_stage INTEGER DEFAULT 1,          -- Initial assigned stage
    last_activity_date DATE,                         -- Last activity date (YYYY-MM-DD)
    updated_at TIMESTAMP DEFAULT NOW(),              -- Last update timestamp
    urdu_enabled BOOLEAN DEFAULT TRUE,               -- Urdu language support enabled
    total_time_spent_minutes INTEGER DEFAULT 0,      -- Total learning time in minutes
    streak_days INTEGER DEFAULT 0,                   -- Current streak in days
    longest_streak INTEGER DEFAULT 0,                 -- Longest streak achieved
    average_session_duration_minutes NUMERIC,        -- Average session duration
    weekly_learning_hours NUMERIC,                   -- Weekly learning hours
    monthly_learning_hours NUMERIC,                  -- Monthly learning hours
    first_activity_date DATE,                        -- First activity date
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Key Fields Used by APIs:**
- `user_id` - Primary identifier
- `current_stage` - Current stage filter
- `current_exercise` - Current exercise
- `overall_progress_percentage` - Progress calculation
- `last_activity_date` - Activity tracking
- `total_time_spent_minutes` - Time metrics
- `total_exercises_completed` - Completion metrics
- `updated_at` - Time range filtering

**Relationships:**
- One record per user
- Updated when user progresses through stages/exercises
- Referenced by multiple analytics endpoints

---

### 2. `ai_tutor_daily_learning_analytics`
**Purpose:** Daily aggregated learning analytics per user

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_daily_learning_analytics (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,                           -- User identifier
    analytics_date DATE NOT NULL,                     -- Date of analytics (YYYY-MM-DD)
    total_time_minutes INTEGER DEFAULT 0,            -- Total time spent in minutes
    sessions_count INTEGER DEFAULT 0,                -- Number of sessions
    average_session_duration NUMERIC,                -- Average session duration in minutes
    exercises_completed INTEGER DEFAULT 0,           -- Exercises completed
    exercises_attempted INTEGER DEFAULT 0,           -- Exercises attempted
    average_score NUMERIC,                           -- Average score
    best_score NUMERIC,                              -- Best score achieved
    urdu_usage_count INTEGER DEFAULT 0,              -- Urdu usage count
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, analytics_date)
);
```

**Key Fields Used by APIs:**
- `user_id` - User identification
- `analytics_date` - Date-based filtering
- `total_time_minutes` - Time calculations
- `sessions_count` - Session metrics
- `exercises_completed` - Completion tracking

**Relationships:**
- One record per user per day
- Created/updated when users complete exercises
- Used for engagement and activity analysis

---

### 3. `ai_tutor_user_topic_progress`
**Purpose:** Tracks user progress at the topic level (most granular)

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_user_topic_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,                           -- User identifier
    stage_id INTEGER NOT NULL,                        -- Stage number (1-6)
    exercise_id INTEGER NOT NULL,                     -- Exercise number (1-3)
    topic_id INTEGER NOT NULL,                        -- Topic number
    attempt_num INTEGER DEFAULT 1,                   -- Attempt number for this topic
    score NUMERIC,                                    -- Score for this attempt
    urdu_used BOOLEAN DEFAULT FALSE,                 -- Whether Urdu was used
    completed BOOLEAN DEFAULT FALSE,                 -- Whether topic was completed
    total_time_seconds INTEGER,                      -- Time spent in seconds
    started_at TIMESTAMP,                            -- When topic was started
    completed_at TIMESTAMP,                          -- When topic was completed
    created_at TIMESTAMP DEFAULT NOW(),              -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, stage_id, exercise_id, topic_id, attempt_num)
);
```

**Key Fields Used by APIs:**
- `user_id` - User identification
- `stage_id` - Stage filtering and grouping
- `exercise_id` - Exercise identification
- `topic_id` - Topic identification
- `attempt_num` - Retry tracking
- `score` - Performance metrics
- `completed` - Completion status
- `created_at` - Time range filtering

**Relationships:**
- Multiple records per user per topic (one per attempt)
- Links to stage through `stage_id`
- Used for lesson access tracking and retry analysis

---

### 4. `ai_tutor_user_exercise_progress`
**Purpose:** Tracks user progress at the exercise level

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_user_exercise_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,                           -- User identifier
    stage_id INTEGER NOT NULL,                        -- Stage number (1-6)
    exercise_id INTEGER NOT NULL,                     -- Exercise number (1-3)
    current_topic_id INTEGER,                         -- Current topic ID
    attempts INTEGER DEFAULT 0,                     -- Total attempts
    scores INTEGER[],                                 -- Array of all scores
    last_5_scores INTEGER[],                         -- Last 5 scores for recent performance
    average_score NUMERIC,                           -- Average score
    best_score NUMERIC,                              -- Best score achieved
    total_score NUMERIC,                             -- Total score accumulated
    urdu_used BOOLEAN[],                             -- Array of Urdu usage flags
    time_spent_minutes INTEGER,                      -- Time spent in minutes
    mature BOOLEAN DEFAULT FALSE,                    -- Maturity status
    started_at TIMESTAMP,                            -- When exercise was started
    completed_at TIMESTAMP,                          -- When exercise was completed
    last_attempt_at TIMESTAMP,                       -- Last attempt timestamp
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, stage_id, exercise_id)
);
```

**Key Fields Used by APIs:**
- `user_id` - User identification
- `stage_id` - Stage filtering
- `exercise_id` - Exercise identification
- `average_score` - Score calculations
- `best_score` - Performance metrics
- `mature` - Maturity tracking

**Relationships:**
- One record per user per exercise
- Updated when user attempts topics within exercise
- Used for score calculations in progress overview

---

### 5. `ai_tutor_user_stage_progress`
**Purpose:** Tracks user progress at the stage level

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_user_stage_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,                           -- User identifier
    stage_id INTEGER NOT NULL,                        -- Stage number (1-6)
    progress_percentage NUMERIC,                     -- Progress percentage (0-100)
    completed BOOLEAN DEFAULT FALSE,                -- Whether stage is completed
    average_score NUMERIC,                           -- Average score across all attempts
    best_score NUMERIC,                              -- Best score achieved
    total_score NUMERIC,                             -- Total score accumulated
    time_spent_minutes INTEGER,                      -- Total time spent in minutes
    attempts_count INTEGER,                          -- Number of attempts
    exercises_completed INTEGER,                     -- Number of exercises completed
    mature BOOLEAN DEFAULT FALSE,                   -- Whether user has reached maturity
    started_at TIMESTAMP,                           -- When stage was first started
    completed_at TIMESTAMP,                         -- When stage was completed
    last_attempt_at TIMESTAMP,                      -- Last attempt timestamp
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, stage_id)
);
```

**Key Fields Used by APIs:**
- `user_id` - User identification
- `stage_id` - Stage filtering
- `progress_percentage` - Progress tracking
- `completed` - Completion status
- `average_score` - Score metrics
- `updated_at` - Time range filtering

**Relationships:**
- One record per user per stage
- Updated when user progresses through a stage
- Used for stage-level progress tracking

---

### 6. `profiles`
**Purpose:** User profile information (name, email, etc.)

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,                             -- User ID (UUID)
    email TEXT,                                       -- User email
    first_name TEXT,                                 -- First name
    last_name TEXT,                                  -- Last name
    role TEXT,                                       -- User role (student, teacher, admin)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Key Fields Used by APIs:**
- `id` - User identifier (matches user_id in other tables)
- `email` - Email address
- `first_name` - First name
- `last_name` - Last name
- `role` - User role

**Relationships:**
- One record per user
- Referenced by all APIs for student name/email lookup
- Used for display names in dashboards

---

### 7. `ai_tutor_content_hierarchy` (Referenced via Cache)
**Purpose:** Stores curriculum structure (stages, exercises, topics)

**Schema (From Previous Documentation):**
```sql
CREATE TABLE ai_tutor_content_hierarchy (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4(),
    level TEXT NOT NULL CHECK (level IN ('stage', 'exercise', 'topic')),
    hierarchy_path TEXT NOT NULL,
    parent_id INTEGER REFERENCES ai_tutor_content_hierarchy(id),
    title TEXT NOT NULL,
    title_urdu TEXT,
    description TEXT,
    description_urdu TEXT,
    stage_number INTEGER,
    difficulty_level TEXT,
    stage_order INTEGER,
    exercise_number INTEGER,
    exercise_type TEXT,
    exercise_order INTEGER,
    topic_number INTEGER,
    topic_order INTEGER,
    content_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Usage:**
- Accessed via cache (`get_all_stages_from_cache()`, `get_stage_by_id()`, `get_exercise_by_ids()`)
- Used for stage/exercise names and metadata
- Not directly queried by these APIs

---

## Data Flow and Processing

### API 1: Overview

#### Step 1: Learn Feature Engagement Summary
1. **Total Students Engaged:**
   - Query: `ai_tutor_user_progress_summary` (filtered by time range)
   - Count unique `user_id` values

2. **Active Today:**
   - Query: `ai_tutor_daily_learning_analytics` where `analytics_date = today`
   - Count unique `user_id` values

3. **Total Time Spent:**
   - Query: `ai_tutor_daily_learning_analytics` (filtered by time range)
   - Sum `total_time_minutes` and convert to hours

4. **Average Responses per Student:**
   - Query: `ai_tutor_user_topic_progress` (filtered by time range)
   - Count total records, divide by total students

5. **Engagement Rate:**
   - Query: `ai_tutor_daily_learning_analytics` (filtered by time range)
   - Count unique users, calculate percentage of total students

6. **Engagement Change:**
   - Compare current period with previous period
   - Calculate percentage change

#### Step 2: Top Used Practice Lessons
1. **Query Topic Progress:**
   - Query: `ai_tutor_user_topic_progress` (filtered by time range)
   - Select: `stage_id`, `exercise_id`, `topic_id`

2. **Count Accesses:**
   - Group by `(stage_id, exercise_id, topic_id)`
   - Count occurrences

3. **Map to Lesson Names:**
   - Use hardcoded mapping (stage_id, exercise_id) → lesson name
   - Calculate trends

4. **Sort and Limit:**
   - Sort by access count (descending)
   - Return top N lessons

---

### API 2: Behavior Insights

#### High Retry Rate Insight
1. **Query Topic Progress:**
   - Query: `ai_tutor_user_topic_progress` (filtered by time range)
   - Select: `user_id`, `stage_id`, `exercise_id`, `topic_id`, `attempt_num`

2. **Calculate Retries:**
   - Group by `user_id`
   - Sum `attempt_num` values
   - Identify users with > 5 total attempts

3. **Batch Fetch Names:**
   - Query: `profiles` table for all affected user IDs
   - Map user_id → student name

4. **Generate Alert:**
   - If any students found, set `has_alert = true`
   - Include details with student names

#### Low Engagement Insight
1. **Get Active Users:**
   - Query: `ai_tutor_daily_learning_analytics` (last 7 days)
   - Get unique `user_id` values

2. **Get Total Users:**
   - Query: `ai_tutor_user_progress_summary`
   - Count total users

3. **Calculate Engagement Rate:**
   - `engagement_rate = (active_users / total_users) * 100`
   - If < 50%, generate alert

#### Inactivity Insight
1. **Get Inactive Students:**
   - Call `_get_inactive_students()` helper
   - Uses `ai_tutor_daily_learning_analytics` and `ai_tutor_user_progress_summary`
   - Identifies users with no activity in last 30 days

2. **Calculate Inactivity Rate:**
   - `inactivity_rate = (inactive_count / total_users) * 100`
   - If > 20%, generate alert

#### Stuck Students Insight
1. **Get Recent Activity:**
   - Query: `ai_tutor_daily_learning_analytics` (last 7 days)
   - Get active user IDs

2. **Get All Users:**
   - Query: `ai_tutor_user_progress_summary`
   - Select: `user_id`, `current_stage`, `last_activity_date`

3. **Identify Stuck Students:**
   - Check `last_activity_date` for each user
   - If inactive for 7+ days and not in recent activity, mark as stuck

4. **Batch Fetch Names:**
   - Query: `profiles` table for stuck user IDs
   - Generate alert with details

---

### API 3: Progress Overview

#### Step 1: Query Student Progress
1. **Base Query:**
   - Query: `ai_tutor_user_progress_summary`
   - Select: `user_id`, `current_stage`, `current_exercise`, `overall_progress_percentage`, `last_activity_date`, `total_time_spent_minutes`, `total_exercises_completed`

2. **Apply Filters:**
   - Filter by `stage_id` if provided
   - Filter by `updated_at` for time range

#### Step 2: Process Each Student
1. **Get Student Info:**
   - Query: `profiles` table for name and email
   - Use `_get_student_name()` and `_get_student_email()`

2. **Calculate Average Score:**
   - Query: `ai_tutor_user_exercise_progress` for current stage
   - Calculate average of `average_score` and `best_score`

3. **Generate AI Feedback:**
   - Call `_generate_ai_feedback()` helper
   - Based on progress percentage and score
   - Returns feedback text and sentiment

4. **Check Risk Status:**
   - `is_at_risk = (progress_percentage < 50) OR (avg_score < 60)`

5. **Apply Search Filter:**
   - If `search_query` provided, filter by name or email

#### Step 3: Calculate Aggregates
1. **Total Students:** Count of filtered students
2. **Average Completion:** Average of `overall_progress_percentage`
3. **Average Score:** Average of all student scores
4. **At Risk Count:** Count of students with `is_at_risk = true`

#### Step 4: Sort and Return
- Sort students by `progress_percentage` (descending)
- Return complete data structure

---

## Helper Functions

### Name Resolution Functions

#### `_get_batch_student_names(user_ids: List[str]) -> Dict[str, str]`
- **Purpose:** Batch fetch student names to avoid N+1 queries
- **Table:** `profiles`
- **Logic:**
  1. Query `profiles` table with `IN` clause for all user IDs
  2. Priority: `first_name + last_name` > `first_name` > `last_name` > `email` > fallback
  3. Returns dictionary: `{user_id: student_name}`

#### `_get_student_name(user_id: str) -> str`
- **Purpose:** Get single student name
- **Table:** `profiles`
- **Logic:** Similar to batch function but for single user

#### `_get_student_email(user_id: str) -> str`
- **Purpose:** Get student email
- **Table:** `profiles`
- **Query:** `SELECT email FROM profiles WHERE id = user_id`

### Score Calculation Functions

#### `_get_student_average_score(user_id: str, stage_id: int) -> float`
- **Purpose:** Calculate student's average score for a stage
- **Table:** `ai_tutor_user_exercise_progress`
- **Logic:**
  1. Query exercises for user and stage
  2. Calculate average of `average_score` and `best_score`
  3. Return overall average

### Feedback Generation

#### `_generate_ai_feedback(record: Dict, avg_score: float) -> Dict`
- **Purpose:** Generate AI-powered feedback for students
- **Logic:**
  - Based on `overall_progress_percentage` and `avg_score`
  - Returns feedback text and sentiment (positive/neutral/negative)
  - Example: "Excellent progress! Keep up the great work." (positive)

### Date Range Helper

#### `_get_date_range(time_range: str) -> tuple`
- **Purpose:** Calculate start and end dates based on time range
- **Returns:** `(start_date, end_date)` or `(None, None)` for "all_time"
- **Options:**
  - "today": Current date only
  - "this_week": Start of week to today
  - "this_month": Start of month to today
  - "this_year": Start of year to today
  - "all_time": No date filtering

---

## Performance Optimizations

### 1. **Caching**
- **Overview API:** 3-minute cache TTL
- **Behavior Insights API:** 5-minute cache TTL
- Uses Redis cache manager with in-memory fallback

### 2. **Parallel Execution**
- **Overview API:** Uses `asyncio.gather()` for concurrent data fetching
- **Behavior Insights API:** All insight calculations run in parallel

### 3. **Batch Queries**
- **Student Names:** Batch fetch all names at once instead of N+1 queries
- **Limits:** Applied to prevent memory issues (e.g., `limit(10000)`)

### 4. **Query Optimization**
- Selective field queries (only fetch needed columns)
- Indexed fields used for filtering (`user_id`, `stage_id`, `analytics_date`)
- Time range filtering applied at database level

---

## Error Handling

- All endpoints catch exceptions and return HTTP 500
- Errors logged using Python logging
- Debug information printed to console
- Graceful fallbacks for missing data

---

## Related Files

1. **Main API File:** `app/routes/teacher_dashboard.py`
2. **Database Client:** `app/supabase_client.py`
3. **Cache Module:** `app/cache.py`
4. **Auth Middleware:** `app/auth_middleware.py`

---

## Notes

- All APIs support time range filtering
- Student names are resolved from `profiles` table
- Progress calculations use multiple tables for accuracy
- Behavior insights use thresholds (e.g., 5 retries, 7 days inactive)
- AI feedback is generated based on progress and scores
- Risk assessment flags students with low progress or scores

