-- =============================================================================
-- Teacher-Student Assignments Table Migration
-- =============================================================================
-- This table establishes the relationship between teachers and their assigned students
-- Required for teacher dashboard filtering to show only assigned students

CREATE TABLE IF NOT EXISTS public.teacher_student_assignments (
    id SERIAL PRIMARY KEY,
    teacher_id TEXT NOT NULL,          -- Teacher's user_id (from profiles table)
    student_id TEXT NOT NULL,          -- Student's user_id (from profiles table)
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by TEXT,                  -- Admin user_id who assigned (optional)
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'removed')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(teacher_id, student_id)
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_teacher_student_assignments_teacher ON public.teacher_student_assignments(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_student_assignments_student ON public.teacher_student_assignments(student_id);
CREATE INDEX IF NOT EXISTS idx_teacher_student_assignments_status ON public.teacher_student_assignments(status);
CREATE INDEX IF NOT EXISTS idx_teacher_student_assignments_active ON public.teacher_student_assignments(teacher_id, status) WHERE status = 'active';

-- Add comments for documentation
COMMENT ON TABLE public.teacher_student_assignments IS 'Maps teachers to their assigned students for dashboard filtering';
COMMENT ON COLUMN public.teacher_student_assignments.teacher_id IS 'User ID of the teacher (from profiles table)';
COMMENT ON COLUMN public.teacher_student_assignments.student_id IS 'User ID of the student (from profiles table)';
COMMENT ON COLUMN public.teacher_student_assignments.status IS 'Assignment status: active (visible to teacher), inactive (temporarily hidden), removed (deleted)';

