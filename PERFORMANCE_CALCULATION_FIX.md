# Performance Calculation Fix for Practice Stage Performance API

## Problem Identified

The `GET /admin/reports/practice-stage-performance` API was returning `performance_percentage: 0` for all stages, even when:
- Stage 1 had 17 users
- Topic-level data showed 96.1% completion rate
- Topic-level data showed 92.6 average score

## Root Cause

The performance calculation was **only using data from `ai_tutor_user_stage_progress` table**, which had:
- 17 users (correct count)
- But all metrics were 0 (progress_percentage, average_score, best_score, time_spent_minutes, attempts_count, etc.)

The calculation formula was:
```
performance = (completion_rate × 30%) + (progress_rate × 20%) + 
              (scores × 25%) + (engagement × 15%) + (maturity × 10%)
```

Since all stage-level metrics were 0, the result was always 0, even though topic-level data existed and showed good performance.

## Solution Implemented

### 1. **Hybrid Data Source Approach**
The fix now uses **both stage-level and topic-level data**:
- **Primary**: Use stage-level data when available and non-zero
- **Fallback**: Use topic-level data when stage-level data is missing or zero

### 2. **Enhanced User Counting**
- Counts unique users from both `ai_tutor_user_stage_progress` and `ai_tutor_user_topic_progress`
- Uses the maximum count to ensure accurate user representation

### 3. **Smart Metric Derivation**
When stage-level data is missing/zero, metrics are derived from topic-level data:

| Metric | Stage Data Source | Topic Data Fallback |
|--------|------------------|---------------------|
| **Completion Rate** | `completed_users / total_users` | `completed_topics / total_topic_attempts` |
| **Progress Rate** | `total_progress / total_users` | `completed_topics / total_topic_attempts` (as percentage) |
| **Average Score** | `total_average_score / total_users` | `total_topic_scores / total_topic_attempts` |
| **Best Score** | `total_best_score / total_users` | `total_topic_scores / total_topic_attempts` (approximation) |
| **Maturity Rate** | `mature_users / total_users` | Based on average topic score (if avg >= 80, consider mature) |
| **Exercise Completion** | `total_exercises_completed / (users × 3)` | `completed_topics / total_topic_attempts` (proxy) |
| **Engagement Score** | `(avg_time × 0.1 + avg_attempts × 2)` | Uses topic time data and attempt counts |

### 4. **Dual Performance Calculation Formulas**

#### When Stage Data is Available:
```
performance = (completion_rate × 30%) + (progress_rate × 20%) + 
              ((avg_score + best_score) / 2 × 25%) + 
              (engagement × 15%) + (maturity × 10%)
```

#### When Only Topic Data is Available:
```
performance = (topic_completion_rate × 35%) + (average_topic_score × 30%) + 
              (engagement × 20%) + (progress_rate × 15%)
```

This formula gives more weight to topic completion and scores when stage-level data isn't available.

## Code Changes

### Key Improvements:

1. **Topic User Tracking**: Added `topic_users_by_stage` dictionary to track unique users per stage from topic progress
2. **Topic Time Tracking**: Added `topic_time_by_stage` dictionary to track total time per stage from topic progress
3. **Data Availability Checks**: Added `has_stage_data` and `has_topic_data` flags to determine which data source to use
4. **Conditional Calculations**: All metrics now check data availability and use appropriate fallback logic
5. **Enhanced Logging**: Added debug output to show calculated performance for each stage

## Expected Results

After this fix, Stage 1 should now show:
- **performance_percentage**: ~85-90% (based on 96.1% topic completion and 92.6 average score)
- **user_count**: 17 (or more if topic data has additional users)
- **All metrics**: Properly calculated from topic data

## Testing

To verify the fix:
1. Call the API: `GET /admin/reports/practice-stage-performance?time_range=all_time`
2. Check that Stage 1 shows a non-zero `performance_percentage`
3. Verify that metrics are calculated correctly:
   - `topic_completion_rate` should be ~96.1%
   - `average_topic_score` should be ~92.6
   - `performance_percentage` should reflect these values

## Files Modified

- `app/routes/admin_dashboard.py` - Updated `_get_practice_stage_performance()` function (lines 567-863)

## Notes

- The fix maintains backward compatibility: if stage-level data exists and is valid, it will be used
- Topic-level data is only used as a fallback when stage-level data is missing or zero
- The calculation now properly reflects user activity even when stage progress table hasn't been updated

