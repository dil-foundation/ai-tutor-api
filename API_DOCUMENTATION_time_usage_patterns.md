# API Documentation: GET /admin/reports/time-usage-patterns

## Overview
This API endpoint retrieves time-of-day usage patterns for a line chart visualization in the admin dashboard. It analyzes user activity patterns across 24 hours of the day based on daily analytics data.

## Endpoint Details

**URL:** `GET /admin/reports/time-usage-patterns`

**Authentication:** Required (Admin or Teacher role)

**Query Parameters:**
- `time_range` (optional, default: "all_time"): Time range filter
  - Options: "today", "this_week", "this_month", "all_time"

**Response Model:** `AdminDashboardResponse`
```json
{
  "success": true,
  "data": {
    "time_patterns": [
      {
        "hour": 0,
        "usage_count": 15,
        "formatted_hour": "00:00"
      },
      {
        "hour": 1,
        "usage_count": 10,
        "formatted_hour": "01:00"
      },
      // ... continues for all 24 hours (0-23)
    ]
  },
  "message": "Time usage patterns data retrieved successfully"
}
```

## Implementation Location
- **File:** `app/routes/admin_dashboard.py`
- **Endpoint Function:** `get_time_usage_patterns()` (line 258)
- **Helper Function:** `_get_time_usage_patterns()` (line 940)
- **Mock Data Function:** `_get_mock_time_patterns()` (line 1161)

---

## Related Database Tables

### 1. `ai_tutor_daily_learning_analytics`
**Purpose:** Tracks daily learning analytics for each user, aggregating activity on a per-day basis

**Schema (Inferred from Code Usage):**
```sql
CREATE TABLE ai_tutor_daily_learning_analytics (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,                        -- User identifier
    analytics_date DATE NOT NULL,                  -- Date of the analytics record (YYYY-MM-DD format)
    total_time_minutes INTEGER DEFAULT 0,         -- Total time spent learning in minutes
    sessions_count INTEGER DEFAULT 0,             -- Number of learning sessions
    average_session_duration NUMERIC,             -- Average duration of sessions in minutes
    exercises_completed INTEGER DEFAULT 0,        -- Number of exercises completed
    exercises_attempted INTEGER DEFAULT 0,        -- Number of exercises attempted
    average_score NUMERIC,                        -- Average score across all exercises
    best_score NUMERIC,                           -- Best score achieved
    urdu_usage_count INTEGER DEFAULT 0,           -- Count of times Urdu was used
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, analytics_date)
);
```

**Key Fields Used by API:**
- `user_id` - Identifies unique users
- `analytics_date` - Used for time range filtering (date-based)
- `total_time_minutes` - Total time spent (used in calculations)
- `sessions_count` - Number of sessions (primary metric for usage distribution)

**Fields Not Used by This API (but exist in table):**
- `average_session_duration` - Available but not used in current implementation
- `exercises_completed` - Available but not used in current implementation
- `exercises_attempted` - Available but not used in current implementation
- `average_score` - Available but not used in current implementation
- `best_score` - Available but not used in current implementation
- `urdu_usage_count` - Available but not used in current implementation

**Relationships:**
- One record per user per day
- Updated/created when user completes exercises or learning activities
- Used by multiple analytics endpoints

**Data Population:**
- Records are created/updated via `_update_daily_analytics()` in `app/supabase_client.py`
- Called automatically when users complete topics/exercises
- Aggregates data from `ai_tutor_user_topic_progress` table

---

## Data Flow and Processing

### 1. **Time Range Filtering**

The API supports different time range filters:

#### "today"
- Filters: `analytics_date = today`
- Returns data only for the current date

#### "this_week"
- Filters: `analytics_date >= start_of_week AND analytics_date <= today`
- Returns data from the start of the current week

#### "this_month"
- Filters: `analytics_date >= start_of_month AND analytics_date <= today`
- Returns data from the start of the current month

#### "all_time"
- Filters: `analytics_date >= (today - 7 days)`
- **Note:** For "all_time", the API only retrieves the last 7 days of data, not all historical data
- This is a performance optimization

### 2. **Data Query Process**

```python
# Query structure
daily_analytics_result = supabase.table('ai_tutor_daily_learning_analytics').select(
    'user_id, total_time_minutes, sessions_count'
).filter_by_date_range().execute()
```

### 3. **Hourly Distribution Algorithm**

**Important Note:** The API does **NOT** have actual hourly data. Since `ai_tutor_daily_learning_analytics` only stores daily aggregates, the API **simulates** hourly distribution using a weighted algorithm.

#### Algorithm Steps:

1. **For each daily record:**
   - Extract `sessions_count` and `total_time_minutes`
   - Calculate `avg_session_duration = total_time_minutes / sessions_count`

2. **Distribute sessions across 24 hours using weighted distribution:**
   - **Peak Hours (weight = 2.0):** 8, 9, 10, 11, 14, 15, 16, 17, 20, 21
     - Morning peak: 8 AM - 11 AM
     - Afternoon peak: 2 PM - 5 PM
     - Evening peak: 8 PM - 9 PM
   
   - **Medium Hours (weight = 1.5):** 12, 13, 18, 19, 22, 23
     - Lunch time: 12 PM - 1 PM
     - Dinner time: 6 PM - 7 PM
     - Late evening: 10 PM - 11 PM
   
   - **Low Hours (weight = 0.5):** All other hours (0-7, 24)
     - Night/early morning hours

3. **Calculation Formula:**
   ```
   For each hour (0-23):
     hour_count = int(sessions_count * weight / 24)
   ```

4. **Aggregate across all daily records:**
   - Sum up the distributed counts for each hour across all days in the time range

### 4. **Mock Data Fallback**

If no data is found in the database, the API returns mock data from `_get_mock_time_patterns()`:

```python
def _get_mock_time_patterns() -> List[Dict[str, Any]]:
    """Get mock time patterns for demonstration"""
    # Returns 24-hour pattern with realistic usage distribution
    # Peak hours: 8-11 AM, 2-5 PM, 6-9 PM
    # Low hours: 12 AM - 6 AM
```

**Mock Data Characteristics:**
- Shows realistic usage patterns
- Peak at 6 PM (160 usage_count)
- Low usage during night hours (2-5 usage_count)
- Gradual increase from 5 AM onwards

### 5. **Response Formatting**

The API returns an array of 24 objects (one for each hour):

```python
time_patterns = []
for hour in range(24):  # 0 to 23
    time_patterns.append({
        'hour': hour,                    # Integer 0-23
        'usage_count': count,            # Aggregated usage count
        'formatted_hour': f"{hour:02d}:00"  # Formatted as "00:00", "01:00", etc.
    })
```

---

## Limitations and Considerations

### 1. **No Actual Hourly Data**
- The table only stores daily aggregates
- Hourly distribution is **simulated** using weighted algorithms
- Results are estimates, not actual hourly usage

### 2. **Weighted Distribution Assumptions**
- Assumes peak usage during typical learning hours (8 AM - 9 PM)
- Distribution is uniform across peak/medium/low hour categories
- May not reflect actual user behavior patterns

### 3. **Time Range Limitation**
- "all_time" only retrieves last 7 days (not truly all time)
- This is a performance optimization

### 4. **Session Count Dependency**
- Algorithm heavily relies on `sessions_count` field
- If `sessions_count` is 0 or missing, that day's data won't contribute to hourly patterns

---

## Potential Improvements

### 1. **Store Actual Hourly Data**
To get accurate hourly patterns, consider:
- Adding an `hour` field to track when sessions occur
- Creating a separate `ai_tutor_hourly_analytics` table
- Tracking session start/end times with timestamps

### 2. **Enhanced Distribution Algorithm**
- Use actual session timestamps if available
- Analyze historical patterns to determine better weights
- Consider timezone information for global users

### 3. **Real-time Data**
- Track session start/end times in real-time
- Store hourly aggregates separately
- Update hourly patterns as sessions occur

---

## Related Files

1. **Main API File:** `app/routes/admin_dashboard.py`
   - Endpoint handler: `get_time_usage_patterns()` (line 258)
   - Core logic: `_get_time_usage_patterns()` (line 940)
   - Mock data: `_get_mock_time_patterns()` (line 1161)
   - Helper: `_get_date_range()` (line 14)

2. **Database Client:** `app/supabase_client.py`
   - `_update_daily_analytics()` - Creates/updates daily analytics records (line 170)
   - Called when users complete topics/exercises

3. **Teacher Dashboard:** `app/routes/teacher_dashboard.py`
   - `_get_student_daily_analytics()` - Uses same table for student analytics (line 2510)

---

## Usage Examples

### Example Request:
```http
GET /admin/reports/time-usage-patterns?time_range=this_week
Authorization: Bearer <token>
```

### Example Response:
```json
{
  "success": true,
  "data": {
    "time_patterns": [
      {"hour": 0, "usage_count": 15, "formatted_hour": "00:00"},
      {"hour": 1, "usage_count": 10, "formatted_hour": "01:00"},
      {"hour": 2, "usage_count": 5, "formatted_hour": "02:00"},
      {"hour": 3, "usage_count": 3, "formatted_hour": "03:00"},
      {"hour": 4, "usage_count": 2, "formatted_hour": "04:00"},
      {"hour": 5, "usage_count": 8, "formatted_hour": "05:00"},
      {"hour": 6, "usage_count": 25, "formatted_hour": "06:00"},
      {"hour": 7, "usage_count": 45, "formatted_hour": "07:00"},
      {"hour": 8, "usage_count": 80, "formatted_hour": "08:00"},
      {"hour": 9, "usage_count": 95, "formatted_hour": "09:00"},
      {"hour": 10, "usage_count": 120, "formatted_hour": "10:00"},
      {"hour": 11, "usage_count": 130, "formatted_hour": "11:00"},
      {"hour": 12, "usage_count": 85, "formatted_hour": "12:00"},
      {"hour": 13, "usage_count": 75, "formatted_hour": "13:00"},
      {"hour": 14, "usage_count": 90, "formatted_hour": "14:00"},
      {"hour": 15, "usage_count": 110, "formatted_hour": "15:00"},
      {"hour": 16, "usage_count": 140, "formatted_hour": "16:00"},
      {"hour": 17, "usage_count": 150, "formatted_hour": "17:00"},
      {"hour": 18, "usage_count": 160, "formatted_hour": "18:00"},
      {"hour": 19, "usage_count": 130, "formatted_hour": "19:00"},
      {"hour": 20, "usage_count": 100, "formatted_hour": "20:00"},
      {"hour": 21, "usage_count": 85, "formatted_hour": "21:00"},
      {"hour": 22, "usage_count": 60, "formatted_hour": "22:00"},
      {"hour": 23, "usage_count": 30, "formatted_hour": "23:00"}
    ]
  },
  "message": "Time usage patterns data retrieved successfully"
}
```

---

## Dependencies

1. **Authentication:** `require_admin_or_teacher` from `app.auth_middleware`
2. **Database:** Supabase client from `app.supabase_client`
3. **Response Model:** `AdminDashboardResponse` (Pydantic model)
4. **Date Utilities:** `_get_date_range()` helper function

---

## Error Handling

- Catches all exceptions and returns HTTP 500 with error message
- Logs errors using Python logging
- Prints debug information to console
- Returns mock data if no real data is found (for demonstration purposes)

---

## Notes

- The hourly distribution is **simulated**, not based on actual hourly timestamps
- The algorithm assumes typical learning patterns (peak during day/evening hours)
- For accurate hourly data, the system would need to track session start/end times
- The "all_time" filter only retrieves the last 7 days for performance reasons
- Mock data is returned when no real data exists, ensuring the frontend always has data to display

