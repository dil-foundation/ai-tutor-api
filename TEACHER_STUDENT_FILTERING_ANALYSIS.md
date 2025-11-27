# Teacher Dashboard APIs - Student Filtering Analysis

## ⚠️ CRITICAL FINDING: No Teacher-Student Filtering

**All three teacher dashboard APIs are returning data for ALL students in the system, not just students assigned to the logged-in teacher.**

---

## Analysis Results

### API 1: `/teacher/dashboard/overview`

**Status:** ❌ **Returns ALL students**

**Evidence:**
```python
# Line 278-282: No teacher filtering
total_students_result = supabase.table('ai_tutor_user_progress_summary').select(
    'user_id'
).execute()  # Gets ALL students

# Line 288-290: No teacher filtering
active_today_result = supabase.table('ai_tutor_daily_learning_analytics').select(
    'user_id'
).eq('analytics_date', today_date).execute()  # Gets ALL active students

# Line 307-311: No teacher filtering
responses_result = supabase.table('ai_tutor_user_topic_progress').select(
    'user_id'
).execute()  # Gets ALL topic progress
```

**Issues:**
- `current_user` is received but **never used** for filtering
- No teacher-student relationship check
- Queries return data for all students in the system

---

### API 2: `/teacher/dashboard/behavior-insights`

**Status:** ❌ **Returns ALL students**

**Evidence:**
```python
# Line 975-982: No teacher filtering
retry_query = supabase.table('ai_tutor_user_topic_progress').select(
    'user_id, stage_id, exercise_id, topic_id, attempt_num'
).limit(10000).execute()  # Gets ALL topic progress

# Line 1145-1152: No teacher filtering
recent_activity_query = supabase.table('ai_tutor_daily_learning_analytics').select(
    'user_id'
).gte('analytics_date', seven_days_ago)  # Gets ALL active users

# Line 1155: No teacher filtering
total_users_result = supabase.table('ai_tutor_user_progress_summary').select(
    'user_id'
).limit(10000).execute()  # Gets ALL users

# Line 1268-1275: No teacher filtering
all_users_query = supabase.table('ai_tutor_user_progress_summary').select(
    'user_id, current_stage, current_exercise, last_activity_date, overall_progress_percentage'
).limit(5000).execute()  # Gets ALL users
```

**Issues:**
- All insight calculations query ALL students
- No filtering by teacher assignment
- `current_user` is not used in any queries

---

### API 3: `/teacher/dashboard/progress-overview`

**Status:** ❌ **Returns ALL students**

**Evidence:**
```python
# Line 1593-1604: No teacher filtering
base_query = supabase.table('ai_tutor_user_progress_summary').select(
    'user_id, current_stage, current_exercise, overall_progress_percentage, last_activity_date, total_time_spent_minutes, total_exercises_completed'
)
# Only filters by stage_id and time_range, NOT by teacher
result = base_query.execute()  # Gets ALL students
```

**Issues:**
- Queries all students from `ai_tutor_user_progress_summary`
- Only applies optional `stage_id` and `time_range` filters
- No teacher-student relationship filtering
- `current_user` parameter is not used for filtering

---

## Missing Components

### 1. **No Teacher-Student Relationship Table**

**Current State:** No table exists to link teachers to students.

**Required Table (Example):**
```sql
CREATE TABLE teacher_student_assignments (
    id SERIAL PRIMARY KEY,
    teacher_id TEXT NOT NULL,          -- Teacher's user_id
    student_id TEXT NOT NULL,          -- Student's user_id
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by TEXT,                  -- Admin who assigned
    status TEXT DEFAULT 'active',      -- active, inactive, removed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(teacher_id, student_id)
);
```

### 2. **No Filtering Logic**

**Current State:** All queries are global, no teacher-specific filtering.

**Required Changes:**
- Add teacher_id filtering to all queries
- Join with teacher-student relationship table
- Filter results to only show assigned students

---

## Security & Privacy Concerns

### 1. **Data Privacy Violation**
- Teachers can see **all students** in the system
- No data isolation between teachers
- Violates privacy expectations

### 2. **Information Leakage**
- Teachers can access student data they shouldn't see
- No access control based on assignments
- Potential GDPR/privacy compliance issues

### 3. **Incorrect Metrics**
- Engagement metrics include students not assigned to teacher
- Behavior insights include unrelated students
- Progress overview shows all students, not just teacher's class

---

## Required Fixes

### Fix 1: Create Teacher-Student Relationship Table

```sql
-- Create teacher-student assignments table
CREATE TABLE IF NOT EXISTS teacher_student_assignments (
    id SERIAL PRIMARY KEY,
    teacher_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'removed')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(teacher_id, student_id),
    FOREIGN KEY (teacher_id) REFERENCES profiles(id),
    FOREIGN KEY (student_id) REFERENCES profiles(id)
);

-- Create indexes for performance
CREATE INDEX idx_teacher_student_assignments_teacher ON teacher_student_assignments(teacher_id);
CREATE INDEX idx_teacher_student_assignments_student ON teacher_student_assignments(student_id);
CREATE INDEX idx_teacher_student_assignments_status ON teacher_student_assignments(status);
```

### Fix 2: Add Helper Function to Get Teacher's Students

```python
async def _get_teacher_student_ids(teacher_id: str) -> List[str]:
    """
    Get list of student IDs assigned to a teacher
    """
    try:
        result = supabase.table('teacher_student_assignments').select(
            'student_id'
        ).eq('teacher_id', teacher_id).eq('status', 'active').execute()
        
        if result.data:
            return [record['student_id'] for record in result.data]
        return []
    except Exception as e:
        print(f"❌ [TEACHER] Error getting teacher students: {str(e)}")
        return []
```

### Fix 3: Update All Queries to Filter by Teacher

#### Example for `/teacher/dashboard/overview`:

```python
async def _get_learn_feature_engagement_summary(time_range: str = "all_time", teacher_id: str = None) -> Dict[str, Any]:
    """
    Get learn feature engagement summary with time range filtering
    NOW INCLUDES TEACHER FILTERING
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        
        # Get teacher's assigned students
        teacher_student_ids = []
        if teacher_id:
            teacher_student_ids = await _get_teacher_student_ids(teacher_id)
            if not teacher_student_ids:
                # Teacher has no assigned students
                return {
                    "total_students_engaged": 0,
                    "active_today": 0,
                    "total_time_spent_hours": 0,
                    # ... other fields with 0 values
                }
        
        # 1. Total Students Engaged - FILTERED BY TEACHER
        if teacher_student_ids:
            if start_date and end_date:
                total_students_result = supabase.table('ai_tutor_user_progress_summary').select(
                    'user_id'
                ).in_('user_id', teacher_student_ids).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat()).execute()
            else:
                total_students_result = supabase.table('ai_tutor_user_progress_summary').select(
                    'user_id'
                ).in_('user_id', teacher_student_ids).execute()
        else:
            # No filtering (admin or no assignments)
            if start_date and end_date:
                total_students_result = supabase.table('ai_tutor_user_progress_summary').select(
                    'user_id'
                ).gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat()).execute()
            else:
                total_students_result = supabase.table('ai_tutor_user_progress_summary').select('user_id').execute()
        
        # Apply same filtering to all other queries...
```

#### Example for `/teacher/dashboard/progress-overview`:

```python
async def _get_student_progress_overview(
    search_query: Optional[str], 
    stage_id: Optional[int], 
    lesson_id: Optional[int], 
    time_range: str,
    teacher_id: str = None  # ADD TEACHER ID PARAMETER
) -> Dict[str, Any]:
    """
    Get comprehensive student progress overview with detailed student data
    NOW INCLUDES TEACHER FILTERING
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        
        # Get teacher's assigned students
        teacher_student_ids = []
        if teacher_id:
            teacher_student_ids = await _get_teacher_student_ids(teacher_id)
            if not teacher_student_ids:
                return {
                    "students": [],
                    "total_students": 0,
                    # ... empty response
                }
        
        # Build base query for student progress
        base_query = supabase.table('ai_tutor_user_progress_summary').select(
            'user_id, current_stage, current_exercise, overall_progress_percentage, last_activity_date, total_time_spent_minutes, total_exercises_completed'
        )
        
        # ADD TEACHER FILTERING
        if teacher_student_ids:
            base_query = base_query.in_('user_id', teacher_student_ids)
        
        # Apply other filters
        if stage_id:
            base_query = base_query.eq('current_stage', stage_id)
        
        if start_date and end_date:
            base_query = base_query.gte('updated_at', start_date.isoformat()).lte('updated_at', end_date.isoformat())
        
        result = base_query.execute()
        # ... rest of the function
```

#### Example for `/teacher/dashboard/behavior-insights`:

```python
async def _get_behavior_insights(time_range: str = "all_time", teacher_id: str = None) -> Dict[str, Any]:
    """
    Get behavior insights (OPTIMIZED with parallel execution)
    NOW INCLUDES TEACHER FILTERING
    """
    try:
        start_date, end_date = _get_date_range(time_range)
        
        # Get teacher's assigned students
        teacher_student_ids = []
        if teacher_id:
            teacher_student_ids = await _get_teacher_student_ids(teacher_id)
        
        # Pass teacher_student_ids to all insight functions
        high_retry_insight, low_engagement_insight, inactivity_insight, stuck_students_insight = await asyncio.gather(
            _get_high_retry_insight(start_date, end_date, teacher_student_ids),
            _get_low_engagement_insight(start_date, end_date, teacher_student_ids),
            _get_inactivity_insight(start_date, end_date, teacher_student_ids),
            _get_stuck_students_insight(start_date, end_date, teacher_student_ids)
        )
        # ... rest of the function
```

### Fix 4: Update Endpoint Functions to Pass Teacher ID

```python
@router.get("/dashboard/overview", response_model=TeacherDashboardResponse)
async def get_teacher_dashboard_overview(
    time_range: str = "all_time",
    current_user: Dict[str, Any] = Depends(require_admin_or_teacher)
):
    """
    Get comprehensive teacher dashboard overview (OPTIMIZED with caching)
    NOW INCLUDES TEACHER FILTERING
    """
    try:
        # Get teacher ID from current_user
        teacher_id = current_user.get('id') if current_user.get('role') == 'teacher' else None
        
        # Pass teacher_id to helper functions
        learn_engagement_summary, top_used_lessons = await asyncio.gather(
            _get_learn_feature_engagement_summary(time_range, teacher_id),
            _get_top_used_practice_lessons(time_range=time_range, teacher_id=teacher_id)
        )
        # ... rest of the function
```

---

## Implementation Checklist

- [ ] Create `teacher_student_assignments` table
- [ ] Add helper function `_get_teacher_student_ids()`
- [ ] Update `_get_learn_feature_engagement_summary()` to filter by teacher
- [ ] Update `_get_top_used_practice_lessons()` to filter by teacher
- [ ] Update `_get_behavior_insights()` to filter by teacher
- [ ] Update `_get_high_retry_insight()` to filter by teacher
- [ ] Update `_get_low_engagement_insight()` to filter by teacher
- [ ] Update `_get_inactivity_insight()` to filter by teacher
- [ ] Update `_get_stuck_students_insight()` to filter by teacher
- [ ] Update `_get_student_progress_overview()` to filter by teacher
- [ ] Update all endpoint functions to extract and pass `teacher_id`
- [ ] Add admin override (admins see all students)
- [ ] Update cache keys to include teacher_id
- [ ] Test with multiple teachers to verify isolation

---

## Current Behavior Summary

| API | Current Behavior | Expected Behavior |
|-----|----------------|-------------------|
| `/teacher/dashboard/overview` | Returns data for **ALL students** | Should return data for **teacher's assigned students only** |
| `/teacher/dashboard/behavior-insights` | Returns insights for **ALL students** | Should return insights for **teacher's assigned students only** |
| `/teacher/dashboard/progress-overview` | Returns progress for **ALL students** | Should return progress for **teacher's assigned students only** |

---

## Recommendations

1. **Immediate Action Required:** This is a **security and privacy issue** that should be fixed immediately.

2. **Database Migration:** Create the `teacher_student_assignments` table and populate it with existing teacher-student relationships (if any exist).

3. **Backward Compatibility:** Consider adding a flag to allow admins to see all students while teachers see only their assigned students.

4. **Testing:** Thoroughly test the filtering to ensure:
   - Teachers only see their assigned students
   - Admins can see all students (if desired)
   - Performance is acceptable with the additional filtering

5. **Documentation:** Update API documentation to clarify that teachers only see their assigned students.

---

## Code Locations to Update

1. **File:** `app/routes/teacher_dashboard.py`
   - Line 155: `get_teacher_dashboard_overview()` - Add teacher_id extraction
   - Line 267: `_get_learn_feature_engagement_summary()` - Add teacher filtering
   - Line 359: `_get_top_used_practice_lessons()` - Add teacher filtering
   - Line 661: `get_behavior_insights()` - Add teacher_id extraction
   - Line 930: `_get_behavior_insights()` - Add teacher filtering
   - Line 968: `_get_high_retry_insight()` - Add teacher filtering
   - Line 1134: `_get_low_engagement_insight()` - Add teacher filtering
   - Line 1202: `_get_inactivity_insight()` - Add teacher filtering
   - Line 1249: `_get_stuck_students_insight()` - Add teacher filtering
   - Line 794: `get_student_progress_overview()` - Add teacher_id extraction
   - Line 1583: `_get_student_progress_overview()` - Add teacher filtering

---

## Notes

- The `current_user` parameter is available in all endpoints but is **not being used** for filtering
- No teacher-student relationship table exists in the current codebase
- All queries are global and return data for all students
- This affects data privacy and may violate compliance requirements

