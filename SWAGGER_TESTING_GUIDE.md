# Testing Teacher-Student Filtering in Swagger Docs

## 📋 Prerequisites

1. **Database Setup**: Run the `teacher_student_assignments_migration.sql` migration
2. **Teacher-Student Assignments**: Create at least one assignment in the database
3. **Test Accounts**: Have at least one teacher and one admin account ready

---

## 🚀 Step-by-Step Testing Guide

### Step 1: Access Swagger Documentation

1. Start your FastAPI server
2. Navigate to Swagger UI:
   ```
   http://localhost:8000/docs
   ```
   Or ReDoc:
   ```
   http://localhost:8000/redoc
   ```

---

### Step 2: Authenticate and Get Token

#### Option A: Using Auth Endpoint (if available)

1. Find the authentication endpoint (usually `/auth/login` or `/auth/token`)
2. Click "Try it out"
3. Enter credentials:
   ```json
   {
     "email": "teacher@example.com",
     "password": "your_password"
   }
   ```
4. Click "Execute"
5. Copy the `access_token` from the response

#### Option B: Using Authorization Header Directly

If you already have a token, you can use it directly in the Authorization header.

---

### Step 3: Set Authorization in Swagger

1. In Swagger UI, click the **"Authorize"** button (🔒 lock icon at the top right)
2. Enter your token:
   - **Format**: `Bearer <your_token>`
   - Example: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
3. Click **"Authorize"**
4. Click **"Close"**

Now all API calls will include this authorization header automatically.

---

### Step 4: Test Teacher Dashboard APIs

#### Test 1: Dashboard Overview (Teacher Account)

**Endpoint**: `GET /teacher/dashboard/overview`

1. Find the endpoint in Swagger
2. Click "Try it out"
3. Set parameters:
   - `time_range`: `"all_time"` (or `"today"`, `"this_week"`, `"this_month"`)
4. Click "Execute"
5. **Expected Result**:
   - Response should only contain data for students assigned to this teacher
   - Check `learn_feature_engagement_summary.total_students_engaged` - should match assigned students count
   - Check `top_used_practice_lessons` - should only show lessons from assigned students

**Verify Filtering**:
```json
{
  "success": true,
  "data": {
    "learn_feature_engagement_summary": {
      "total_students_engaged": 5,  // Should match assigned students
      "active_today": 3,
      // ... other metrics
    },
    "top_used_practice_lessons": [
      // Only lessons from assigned students
    ]
  }
}
```

---

#### Test 2: Behavior Insights (Teacher Account)

**Endpoint**: `GET /teacher/dashboard/behavior-insights`

1. Click "Try it out"
2. Set `time_range`: `"all_time"`
3. Click "Execute"
4. **Expected Result**:
   - All insights should only show assigned students
   - `high_retry_rate.affected_students` - only assigned students
   - `low_engagement.affected_students` - only assigned students
   - `inactivity.affected_students` - only assigned students
   - `stuck_students.affected_students` - only assigned students

**Verify Filtering**:
```json
{
  "success": true,
  "data": {
    "high_retry_rate": {
      "affected_students": 2,  // Only assigned students
      "details": {
        "students": [
          // Only assigned students in the list
        ]
      }
    },
    "low_engagement": {
      "affected_students": 1,  // Only assigned students
      // ...
    }
  }
}
```

---

#### Test 3: Progress Overview (Teacher Account)

**Endpoint**: `GET /teacher/dashboard/progress-overview`

1. Click "Try it out"
2. Set parameters:
   - `time_range`: `"all_time"`
   - `search_query`: (optional)
   - `stage_id`: (optional)
   - `lesson_id`: (optional)
3. Click "Execute"
4. **Expected Result**:
   - `students` array should only contain assigned students
   - `total_students` should match assigned students count

**Verify Filtering**:
```json
{
  "success": true,
  "data": {
    "students": [
      {
        "user_id": "student_id_1",  // Assigned student
        "student_name": "John Doe",
        // ...
      },
      {
        "user_id": "student_id_2",  // Assigned student
        "student_name": "Jane Smith",
        // ...
      }
      // Should NOT contain unassigned students
    ],
    "total_students": 2,  // Should match assigned students count
    "avg_completion_percentage": 75.5,
    // ...
  }
}
```

---

### Step 5: Test with Admin Account

1. **Logout/Change Authorization**:
   - Click "Authorize" button again
   - Clear the token or enter an admin token
   - Click "Authorize"

2. **Repeat the same tests** with admin account

3. **Expected Result**:
   - Admin should see **ALL students** (not filtered)
   - `total_students` should be higher than teacher's view
   - All student data should be visible

**Verify Admin Access**:
```json
{
  "success": true,
  "data": {
    "students": [
      // ALL students in the system
    ],
    "total_students": 50,  // All students, not just assigned
    // ...
  }
}
```

---

### Step 6: Compare Teacher vs Admin Results

**Side-by-Side Comparison**:

| Metric | Teacher Account | Admin Account |
|--------|----------------|---------------|
| `total_students_engaged` | 5 (assigned only) | 50 (all students) |
| `total_students` (progress) | 5 (assigned only) | 50 (all students) |
| `affected_students` (insights) | Only assigned | All students |

---

## 🔍 Detailed Testing Scenarios

### Scenario 1: Teacher with No Assigned Students

1. Use a teacher account with **no students assigned**
2. Call any dashboard endpoint
3. **Expected**: Empty results or zero counts
   ```json
   {
     "data": {
       "total_students_engaged": 0,
       "students": [],
       "total_students": 0
     }
   }
   ```

### Scenario 2: Teacher with Multiple Assigned Students

1. Use a teacher account with **multiple students assigned**
2. Call dashboard endpoints
3. **Expected**: Only those specific students appear in results
4. **Verify**: Count matches number of assigned students

### Scenario 3: Cache Isolation

1. Login as **Teacher A**, call `/teacher/dashboard/overview`
2. Login as **Teacher B**, call `/teacher/dashboard/overview`
3. **Expected**: Different results (different cached data)
4. **Verify**: Cache keys include `teacher_id` in logs

---

## 🧪 Quick Test Checklist

### Teacher Account Tests:
- [ ] `/teacher/dashboard/overview` - Only shows assigned students
- [ ] `/teacher/dashboard/behavior-insights` - Only shows assigned students
- [ ] `/teacher/dashboard/progress-overview` - Only shows assigned students
- [ ] `/teacher/dashboard/learn-engagement-summary` - Only shows assigned students
- [ ] `/teacher/dashboard/top-used-lessons` - Only shows assigned students
- [ ] `/teacher/dashboard/high-retry-students` - Only shows assigned students
- [ ] `/teacher/dashboard/stuck-students` - Only shows assigned students
- [ ] `/teacher/dashboard/inactive-students` - Only shows assigned students

### Admin Account Tests:
- [ ] All endpoints show **ALL students** (not filtered)
- [ ] Counts are higher than teacher's view

### Edge Cases:
- [ ] Teacher with no assigned students → Empty results
- [ ] Teacher with one assigned student → Only that student
- [ ] Cache isolation between different teachers

---

## 📊 Sample Test Data Setup

### 1. Create Teacher-Student Assignments

```sql
-- Example: Assign 3 students to teacher_1
INSERT INTO teacher_student_assignments (teacher_id, student_id, assigned_by, status)
VALUES 
    ('teacher_user_id_1', 'student_user_id_1', 'admin_user_id', 'active'),
    ('teacher_user_id_1', 'student_user_id_2', 'admin_user_id', 'active'),
    ('teacher_user_id_1', 'student_user_id_3', 'admin_user_id', 'active');

-- Assign 2 different students to teacher_2
INSERT INTO teacher_student_assignments (teacher_id, student_id, assigned_by, status)
VALUES 
    ('teacher_user_id_2', 'student_user_id_4', 'admin_user_id', 'active'),
    ('teacher_user_id_2', 'student_user_id_5', 'admin_user_id', 'active');
```

### 2. Verify Assignments

```sql
-- Check assignments for a teacher
SELECT * FROM teacher_student_assignments 
WHERE teacher_id = 'teacher_user_id_1' AND status = 'active';

-- Count assigned students
SELECT COUNT(*) FROM teacher_student_assignments 
WHERE teacher_id = 'teacher_user_id_1' AND status = 'active';
```

---

## 🐛 Troubleshooting

### Issue: Teacher sees all students

**Possible Causes**:
1. `teacher_student_assignments` table doesn't exist
2. No assignments created for the teacher
3. `teacher_id` not being extracted correctly

**Solution**:
1. Check database migration was run
2. Verify assignments exist: `SELECT * FROM teacher_student_assignments WHERE teacher_id = 'your_teacher_id'`
3. Check server logs for `teacher_id` extraction

### Issue: Admin sees no students

**Possible Causes**:
1. Filtering logic incorrectly applied to admin

**Solution**:
1. Verify `teacher_id` is `None` for admin
2. Check that empty list from `_get_teacher_student_ids(None)` doesn't filter

### Issue: Cache showing wrong data

**Possible Causes**:
1. Cache keys not including `teacher_id`

**Solution**:
1. Clear cache or wait for TTL to expire
2. Verify cache keys include `teacher_id` in code

---

## 📝 Expected Response Examples

### Teacher Response (Filtered):
```json
{
  "success": true,
  "data": {
    "learn_feature_engagement_summary": {
      "total_students_engaged": 3,
      "active_today": 2,
      "total_time_spent_hours": 45.5
    },
    "top_used_practice_lessons": [
      {
        "lesson_name": "Daily Routine Conversations",
        "accesses": 15
      }
    ]
  }
}
```

### Admin Response (All Students):
```json
{
  "success": true,
  "data": {
    "learn_feature_engagement_summary": {
      "total_students_engaged": 50,  // All students
      "active_today": 35,
      "total_time_spent_hours": 450.5
    },
    "top_used_practice_lessons": [
      {
        "lesson_name": "Daily Routine Conversations",
        "accesses": 150  // More accesses (all students)
      }
    ]
  }
}
```

---

## ✅ Success Criteria

The implementation is working correctly if:

1. ✅ Teachers only see their assigned students
2. ✅ Admins see all students
3. ✅ Different teachers see different data
4. ✅ Cache is isolated per teacher
5. ✅ No data leakage between teachers
6. ✅ Empty results for teachers with no assignments

---

## 🔗 Related Documentation

- `TEACHER_FILTERING_IMPLEMENTATION.md` - Implementation details
- `teacher_student_assignments_migration.sql` - Database schema
- `TEACHER_STUDENT_FILTERING_ANALYSIS.md` - Original analysis

---

**Happy Testing! 🚀**

