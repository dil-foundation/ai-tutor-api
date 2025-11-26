# API Documentation: GET /admin/reports/practice-stage-performance

## Overview
This API endpoint retrieves practice stage performance data for a bar chart visualization in the admin dashboard. It calculates comprehensive performance metrics for all 6 stages based on multiple factors including completion rates, scores, engagement, and maturity.

## Endpoint Details

**URL:** `GET /admin/reports/practice-stage-performance`

**Authentication:** Required (Admin or Teacher role)

**Query Parameters:**
- `time_range` (optional, default: "all_time"): Time range filter
  - Options: "today", "this_week", "this_month", "all_time"

**Response Model:** `AdminDashboardResponse`
```json
{
  "success": true,
  "data": {
    "stages": [
      {
        "stage_id": 1,
        "stage_name": "Stage Name",
        "performance_percentage": 75.5,
        "user_count": 150,
        "color": "#3B82F6",
        "metrics": {
          "completion_rate": 60.0,
          "progress_rate": 70.0,
          "average_score": 75.0,
          "best_score": 85.0,
          "maturity_rate": 40.0,
          "exercise_completion_rate": 65.0,
          "topic_completion_rate": 70.0,
          "average_topic_score": 72.0,
          "engagement_score": 55.0
        }
      }
    ]
  },
  "message": "Practice stage performance data retrieved successfully"
}
```

## Implementation Location
- **File:** `app/routes/admin_dashboard.py`
- **Function:** `get_practice_stage_performance()` (line 206)
- **Helper Function:** `_get_practice_stage_performance()` (line 567)

---

## Related Database Tables

### 1. `ai_tutor_user_stage_progress`
**Purpose:** Tracks user progress at the stage level (stages 1-6)

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_user_stage_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,                    -- User identifier
    stage_id INTEGER NOT NULL,                -- Stage number (1-6)
    progress_percentage NUMERIC,              -- Progress percentage (0-100)
    completed BOOLEAN DEFAULT FALSE,          -- Whether stage is completed
    average_score NUMERIC,                    -- Average score across all attempts
    best_score NUMERIC,                       -- Best score achieved
    total_score NUMERIC,                     -- Total score accumulated
    time_spent_minutes INTEGER,              -- Total time spent in minutes
    attempts_count INTEGER,                  -- Number of attempts
    exercises_completed INTEGER,             -- Number of exercises completed
    mature BOOLEAN DEFAULT FALSE,            -- Whether user has reached maturity
    started_at TIMESTAMP,                    -- When stage was first started
    completed_at TIMESTAMP,                  -- When stage was completed
    last_attempt_at TIMESTAMP,               -- Last attempt timestamp
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, stage_id)
);
```

**Key Fields Used by API:**
- `stage_id` - Groups data by stage
- `user_id` - Identifies unique users
- `progress_percentage` - Used in performance calculation
- `completed` - Used for completion rate
- `average_score` - Used in score calculations
- `best_score` - Used in score calculations
- `time_spent_minutes` - Used for engagement metrics
- `attempts_count` - Used for engagement metrics
- `exercises_completed` - Used for exercise completion rate
- `mature` - Used for maturity rate
- `updated_at` - Used for time range filtering

**Relationships:**
- One record per user per stage
- Updated when user progresses through a stage

---

### 2. `ai_tutor_user_topic_progress`
**Purpose:** Tracks user progress at the topic level (most granular level)

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_user_topic_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,                    -- User identifier
    stage_id INTEGER NOT NULL,                -- Stage number (1-6)
    exercise_id INTEGER NOT NULL,             -- Exercise number (1-3)
    topic_id INTEGER NOT NULL,                -- Topic number
    attempt_num INTEGER DEFAULT 1,            -- Attempt number for this topic
    score NUMERIC,                            -- Score for this attempt
    urdu_used BOOLEAN DEFAULT FALSE,          -- Whether Urdu was used
    completed BOOLEAN DEFAULT FALSE,          -- Whether topic was completed
    total_time_seconds INTEGER,              -- Time spent in seconds
    started_at TIMESTAMP,                    -- When topic was started
    completed_at TIMESTAMP,                  -- When topic was completed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, stage_id, exercise_id, topic_id, attempt_num)
);
```

**Key Fields Used by API:**
- `stage_id` - Groups data by stage
- `user_id` - Identifies unique users
- `score` - Used for average topic score calculation
- `completed` - Used for topic completion rate
- `total_time_seconds` - Used for time-based metrics
- `created_at` - Used for time range filtering

**Relationships:**
- Multiple records per user per topic (one per attempt)
- Links to stage through `stage_id`
- More granular than stage progress

---

### 3. `ai_tutor_content_hierarchy`
**Purpose:** Stores the curriculum structure (stages, exercises, topics)

**Schema (From SQL File):**
```sql
CREATE TABLE ai_tutor_content_hierarchy (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4(),
    level TEXT NOT NULL CHECK (level IN ('stage', 'exercise', 'topic')),
    hierarchy_path TEXT NOT NULL,            -- e.g., "1", "1.1", "1.1.1"
    parent_id INTEGER REFERENCES ai_tutor_content_hierarchy(id),
    title TEXT NOT NULL,
    title_urdu TEXT,
    description TEXT,
    description_urdu TEXT,
    
    -- Stage-specific fields
    stage_number INTEGER,
    difficulty_level TEXT CHECK (difficulty_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
    stage_order INTEGER,
    
    -- Exercise-specific fields
    exercise_number INTEGER,
    exercise_type TEXT CHECK (exercise_type IN ('pronunciation', 'response', 'dialogue', 'narration', 'conversation', 'roleplay', 'storytelling', 'discussion', 'problem_solving', 'presentation', 'negotiation', 'leadership', 'debate', 'academic', 'interview', 'spontaneous', 'diplomatic', 'academic_debate')),
    exercise_order INTEGER,
    
    -- Topic-specific fields
    topic_number INTEGER,
    topic_order INTEGER,
    
    -- Flexible data storage
    content_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Key Fields Used by API:**
- `stage_number` - Maps to stage_id
- `title` - Used for stage_name in response
- `level` - Filters for stage-level records

**Relationships:**
- Hierarchical structure: Stage → Exercise → Topic
- Used via cache (`get_all_stages_from_cache()`) to get stage names

---

## Data Flow and Processing

### 1. **Time Range Filtering**
The API supports time range filtering through `_get_date_range()`:
- **"today"**: Current date only
- **"this_week"**: From start of week to today
- **"this_month"**: From start of month to today
- **"all_time"**: No date filtering

### 2. **Data Aggregation Process**

#### Step 1: Initialize Stage Data
- Creates data structures for all 6 stages (1-6)
- Gets stage names dynamically from cache (`get_all_stages_from_cache()`)

#### Step 2: Fetch Stage Progress Data
- Queries `ai_tutor_user_stage_progress` table
- Filters by `updated_at` if time range is specified
- Aggregates:
  - Total users per stage
  - Completed users count
  - Total progress percentages
  - Total average scores
  - Total best scores
  - Total time spent
  - Total attempts
  - Total exercises completed
  - Mature users count

#### Step 3: Fetch Topic Progress Data
- Queries `ai_tutor_user_topic_progress` table
- Filters by `created_at` if time range is specified
- Aggregates:
  - Total topic attempts per stage
  - Total topic scores
  - Completed topics count

#### Step 4: Calculate Performance Metrics
For each stage, calculates:

1. **Completion Rate** = (completed_users / total_users) × 100
2. **Progress Rate** = total_progress / total_users
3. **Average Score Rate** = total_average_score / total_users
4. **Best Score Rate** = total_best_score / total_users
5. **Maturity Rate** = (mature_users / total_users) × 100
6. **Exercise Completion Rate** = (total_exercises_completed / (total_users × 3)) × 100
7. **Topic Completion Rate** = (completed_topics / total_topic_attempts) × 100
8. **Average Topic Score** = total_topic_scores / total_topic_attempts
9. **Engagement Score** = min(100, (avg_time_per_user × 0.1 + avg_attempts_per_user × 2))

#### Step 5: Calculate Weighted Performance
Weighted formula:
```
Performance = (Completion × 30%) + (Progress × 20%) + 
              ((Avg Score + Best Score) / 2 × 25%) + 
              (Engagement × 15%) + (Maturity × 10%)
```

### 3. **Response Formatting**
- Returns all 6 stages, even if some have 0% performance
- Sorts by performance percentage (descending)
- Includes color coding per stage
- Includes detailed metrics for debugging/insights

---

## Related Files

1. **Main API File:** `app/routes/admin_dashboard.py`
   - Endpoint handler: `get_practice_stage_performance()` (line 206)
   - Core logic: `_get_practice_stage_performance()` (line 567)
   - Helper: `_get_date_range()` (line 14)
   - Helper: `_get_stage_color()` (line 997)

2. **Cache Module:** `app/cache.py`
   - `get_all_stages_from_cache()` - Retrieves stage names
   - `get_stage_by_id()` - Gets stage by ID
   - `get_exercise_by_ids()` - Gets exercise by IDs

3. **Database Client:** `app/supabase_client.py`
   - Supabase client initialization
   - Progress tracking operations

4. **Content Hierarchy:** `ai_tutor_optimized_hierarchical_structure.sql`
   - Database schema for content structure

---

## Performance Calculation Details

### Weight Distribution:
- **Completion Rate (30%)**: How many users completed the stage
- **Progress Rate (20%)**: Average progress percentage
- **Score Metrics (25%)**: Average of average_score and best_score
- **Engagement Score (15%)**: Based on time spent and attempts
- **Maturity Rate (10%)**: Users who reached maturity level

### Engagement Score Formula:
```
avg_time_per_user = total_time_spent / total_users
avg_attempts_per_user = total_attempts / total_users
engagement_score = min(100, (avg_time_per_user × 0.1 + avg_attempts_per_user × 2))
```

### Exercise Completion Rate:
Assumes each stage has 3 exercises:
```
max_exercises = total_users × 3
exercise_completion_rate = (total_exercises_completed / max_exercises) × 100
```

---

## Dependencies

1. **Authentication:** `require_admin_or_teacher` from `app.auth_middleware`
2. **Database:** Supabase client from `app.supabase_client`
3. **Cache:** Stage data from `app.cache`
4. **Response Model:** `AdminDashboardResponse` (Pydantic model)

---

## Error Handling

- Catches all exceptions and returns HTTP 500 with error message
- Logs errors using Python logging
- Prints debug information to console
- Returns empty array if no data found (all stages still returned with 0% performance)

---

## Notes

- The API always returns all 6 stages, even if they have no data (0% performance)
- Stage names are fetched dynamically from cache, not hardcoded
- Time range filtering uses different date fields:
  - Stage progress: `updated_at`
  - Topic progress: `created_at`
- Performance calculation is comprehensive, using multiple weighted factors
- Color coding is predefined per stage ID (1-6)

