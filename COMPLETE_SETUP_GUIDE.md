# Complete Setup Guide for Teacher-Student Filtering

## ❌ SQL Script Alone is NOT Enough

The `teacher_student_assignments_migration.sql` script only creates the **table structure**. You need **3 components** for the filtering to work:

---

## ✅ Required Components

### 1. **Database Table** (✅ SQL Script Provides This)
- Creates the `teacher_student_assignments` table
- Sets up indexes for performance
- **Status**: ✅ Already created in the script

### 2. **Application Code** (✅ Already Implemented)
- `_get_teacher_student_ids()` function queries the table
- All dashboard functions filter by teacher
- **Status**: ✅ Already implemented in `teacher_dashboard.py`

### 3. **Data in the Table** (❌ **YOU NEED TO ADD THIS**)
- Actual teacher-student assignments
- **Status**: ❌ **MISSING - You need to populate this**

---

## 🚀 Complete Setup Steps

### Step 1: Run the SQL Migration ✅

Execute the migration script in your Supabase database:

```sql
-- Run teacher_student_assignments_migration.sql
-- This creates the table structure
```

**Verify it worked:**
```sql
-- Check if table exists
SELECT * FROM information_schema.tables 
WHERE table_name = 'teacher_student_assignments';

-- Should return the table definition
```

---

### Step 2: Populate Teacher-Student Assignments ❌ **CRITICAL STEP**

**This is what's missing!** You need to insert actual assignment data:

```sql
-- Example: Assign students to teachers
INSERT INTO teacher_student_assignments (teacher_id, student_id, assigned_by, status)
VALUES 
    -- Teacher 1's students
    ('teacher_user_id_1', 'student_user_id_1', 'admin_user_id', 'active'),
    ('teacher_user_id_1', 'student_user_id_2', 'admin_user_id', 'active'),
    ('teacher_user_id_1', 'student_user_id_3', 'admin_user_id', 'active'),
    
    -- Teacher 2's students
    ('teacher_user_id_2', 'student_user_id_4', 'admin_user_id', 'active'),
    ('teacher_user_id_2', 'student_user_id_5', 'admin_user_id', 'active');
```

**How to get the user IDs:**

```sql
-- Get teacher user IDs
SELECT id, email, role FROM profiles WHERE role = 'teacher';

-- Get student user IDs
SELECT id, email, role FROM profiles WHERE role = 'student';

-- Get admin user ID (for assigned_by field)
SELECT id, email, role FROM profiles WHERE role = 'admin' LIMIT 1;
```

---

### Step 3: Verify Assignments

```sql
-- Check assignments for a specific teacher
SELECT 
    tsa.teacher_id,
    t.email as teacher_email,
    tsa.student_id,
    s.email as student_email,
    tsa.status,
    tsa.assigned_at
FROM teacher_student_assignments tsa
JOIN profiles t ON tsa.teacher_id = t.id
JOIN profiles s ON tsa.student_id = s.id
WHERE tsa.teacher_id = 'your_teacher_user_id'
AND tsa.status = 'active';

-- Count assigned students per teacher
SELECT 
    teacher_id,
    COUNT(*) as assigned_students_count
FROM teacher_student_assignments
WHERE status = 'active'
GROUP BY teacher_id;
```

---

## 📋 What Each Component Does

### Component 1: SQL Script (Table Structure)
```sql
CREATE TABLE teacher_student_assignments (...)
```
- **Purpose**: Creates the container for assignments
- **Status**: ✅ Done (script provided)

### Component 2: Application Code (Filtering Logic)
```python
async def _get_teacher_student_ids(teacher_id):
    result = supabase.table('teacher_student_assignments').select(
        'student_id'
    ).eq('teacher_id', teacher_id).eq('status', 'active').execute()
    return [record['student_id'] for record in result.data]
```
- **Purpose**: Queries the table to get assigned students
- **Status**: ✅ Done (already implemented)

### Component 3: Data (Actual Assignments) ⚠️ **YOU NEED THIS**
```sql
INSERT INTO teacher_student_assignments VALUES (...)
```
- **Purpose**: Stores which students belong to which teacher
- **Status**: ❌ **YOU NEED TO ADD THIS**

---

## 🔍 How to Check if Everything is Working

### Test 1: Check if Table Exists
```sql
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_name = 'teacher_student_assignments'
);
-- Should return: true
```

### Test 2: Check if Data Exists
```sql
SELECT COUNT(*) FROM teacher_student_assignments WHERE status = 'active';
-- Should return: > 0 (if you've added assignments)
```

### Test 3: Check Application Code
```python
# In your Python code, this function should work:
teacher_student_ids = await _get_teacher_student_ids('teacher_user_id')
print(f"Assigned students: {teacher_student_ids}")
# Should print: ['student_id_1', 'student_id_2', ...]
```

---

## ⚠️ Common Issues

### Issue 1: "No students showing for teacher"
**Cause**: No assignments in the table
**Solution**: Run INSERT statements to create assignments

### Issue 2: "Teacher sees all students"
**Cause**: 
- Table doesn't exist (migration not run)
- No assignments for that teacher
- `teacher_id` not matching

**Solution**:
```sql
-- Check if assignments exist
SELECT * FROM teacher_student_assignments 
WHERE teacher_id = 'your_teacher_id' AND status = 'active';
```

### Issue 3: "Table doesn't exist error"
**Cause**: Migration not run
**Solution**: Execute `teacher_student_assignments_migration.sql`

---

## 📝 Quick Setup Script

Here's a complete setup script you can run:

```sql
-- Step 1: Create table (if not exists)
-- Run: teacher_student_assignments_migration.sql

-- Step 2: Get your user IDs
-- Replace these with actual IDs from your profiles table
DO $$
DECLARE
    teacher_1_id TEXT := 'your_teacher_1_id';
    teacher_2_id TEXT := 'your_teacher_2_id';
    student_1_id TEXT := 'your_student_1_id';
    student_2_id TEXT := 'your_student_2_id';
    student_3_id TEXT := 'your_student_3_id';
    admin_id TEXT := 'your_admin_id';
BEGIN
    -- Insert assignments
    INSERT INTO teacher_student_assignments (teacher_id, student_id, assigned_by, status)
    VALUES 
        (teacher_1_id, student_1_id, admin_id, 'active'),
        (teacher_1_id, student_2_id, admin_id, 'active'),
        (teacher_2_id, student_3_id, admin_id, 'active')
    ON CONFLICT (teacher_id, student_id) DO NOTHING;
END $$;

-- Step 3: Verify
SELECT 
    t.email as teacher,
    s.email as student,
    tsa.status
FROM teacher_student_assignments tsa
JOIN profiles t ON tsa.teacher_id = t.id
JOIN profiles s ON tsa.student_id = s.id
WHERE tsa.status = 'active';
```

---

## ✅ Summary

| Component | Status | What It Does |
|-----------|--------|--------------|
| **SQL Script** | ✅ Provided | Creates table structure |
| **Application Code** | ✅ Implemented | Queries table and filters data |
| **Assignment Data** | ❌ **YOU NEED THIS** | Stores teacher-student relationships |

---

## 🎯 Next Steps

1. ✅ Run `teacher_student_assignments_migration.sql` (if not done)
2. ❌ **Insert teacher-student assignments** (CRITICAL - missing step)
3. ✅ Test in Swagger (see `SWAGGER_TESTING_GUIDE.md`)

---

**The SQL script creates the foundation, but you MUST populate it with actual assignment data for the filtering to work!**

