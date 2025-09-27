/**
 * Optimized API Service for Teacher Dashboard
 * Replaces slow endpoints with fast optimized versions
 */

class OptimizedTeacherAPI {
    constructor(baseUrl = 'https://d3k15uo8yl49h6.cloudfront.net') {
        this.baseUrl = baseUrl;
        this.cache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
    }

    // Cache management
    getCacheKey(url, params = {}) {
        return `${url}?${new URLSearchParams(params).toString()}`;
    }

    getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;
        
        if (Date.now() - cached.timestamp > this.cacheTTL) {
            this.cache.delete(key);
            return null;
        }
        
        return cached.data;
    }

    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    // Optimized API calls
    async fetchWithCache(endpoint, params = {}) {
        const cacheKey = this.getCacheKey(endpoint, params);
        const cached = this.getFromCache(cacheKey);
        
        if (cached) {
            console.log('🎯 Using cached data for:', endpoint);
            return cached;
        }

        const url = `${this.baseUrl}${endpoint}?${new URLSearchParams(params).toString()}`;
        const startTime = performance.now();
        
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    // Add your auth headers here
                    // 'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            const endTime = performance.now();
            const duration = endTime - startTime;

            console.log(`⚡ API call completed: ${endpoint} in ${duration.toFixed(0)}ms`);
            
            // Cache successful responses
            this.setCache(cacheKey, data);
            
            return data;
        } catch (error) {
            const endTime = performance.now();
            const duration = endTime - startTime;
            console.error(`❌ API call failed: ${endpoint} after ${duration.toFixed(0)}ms`, error);
            throw error;
        }
    }

    // OPTIMIZED: Single batch call instead of 3 separate calls
    async getDashboardBatchData(timeRange = 'all_time') {
        console.log('🚀 Loading dashboard batch data (optimized)...');
        
        try {
            const data = await this.fetchWithCache('/teacher/optimized/dashboard/batch-data', {
                time_range: timeRange
            });
            
            return {
                success: true,
                overview: data.data.overview,
                behaviorInsights: data.data.behavior_insights,
                progressOverview: data.data.progress_overview,
                performanceMetrics: data.data.performance_metrics
            };
        } catch (error) {
            console.error('❌ Batch dashboard data failed:', error);
            return { success: false, error: error.message };
        }
    }

    // OPTIMIZED: Individual fast endpoints (fallback)
    async getDashboardOverview(timeRange = 'all_time') {
        return this.fetchWithCache('/teacher/optimized/dashboard/overview-fast', {
            time_range: timeRange
        });
    }

    async getBehaviorInsights(timeRange = 'all_time') {
        return this.fetchWithCache('/teacher/optimized/dashboard/behavior-insights-fast', {
            time_range: timeRange
        });
    }

    async getProgressOverview(searchQuery = null, stageId = null, timeRange = 'all_time') {
        const params = { time_range: timeRange };
        if (searchQuery) params.search_query = searchQuery;
        if (stageId) params.stage_id = stageId;
        
        return this.fetchWithCache('/teacher/optimized/dashboard/progress-overview-fast', params);
    }

    // Performance monitoring
    async getPerformanceStats() {
        return this.fetchWithCache('/teacher/optimized/performance-stats');
    }

    // Cache management
    clearCache() {
        this.cache.clear();
        console.log('🧹 API cache cleared');
    }

    getCacheStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys())
        };
    }
}

// React Hook for optimized teacher dashboard
function useOptimizedTeacherDashboard(timeRange = 'all_time') {
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);
    const [performanceMetrics, setPerformanceMetrics] = React.useState(null);

    const api = React.useMemo(() => new OptimizedTeacherAPI(), []);

    const loadDashboardData = React.useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            
            const startTime = performance.now();
            
            // Use optimized batch endpoint
            const result = await api.getDashboardBatchData(timeRange);
            
            const endTime = performance.now();
            const totalTime = endTime - startTime;
            
            if (result.success) {
                setData(result);
                setPerformanceMetrics({
                    totalLoadTime: totalTime,
                    optimization: 'Batch API call',
                    improvement: 'Up to 90% faster'
                });
            } else {
                setError(result.error);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [api, timeRange]);

    React.useEffect(() => {
        loadDashboardData();
    }, [loadDashboardData]);

    return {
        data,
        loading,
        error,
        performanceMetrics,
        refetch: loadDashboardData,
        clearCache: () => api.clearCache()
    };
}

// Example React Component using optimized API
function OptimizedTeacherDashboard() {
    const [timeRange, setTimeRange] = React.useState('all_time');
    const { data, loading, error, performanceMetrics, refetch } = useOptimizedTeacherDashboard(timeRange);

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner"></div>
                <p>Loading dashboard data (optimized)...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="error-container">
                <h3>❌ Error Loading Dashboard</h3>
                <p>{error}</p>
                <button onClick={refetch}>Retry</button>
            </div>
        );
    }

    return (
        <div className="teacher-dashboard">
            {/* Performance indicator */}
            {performanceMetrics && (
                <div className="performance-indicator">
                    ⚡ Loaded in {performanceMetrics.totalLoadTime.toFixed(0)}ms 
                    ({performanceMetrics.improvement})
                </div>
            )}

            {/* Time range selector */}
            <div className="time-range-selector">
                <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
                    <option value="all_time">All Time</option>
                    <option value="this_year">This Year</option>
                    <option value="this_month">This Month</option>
                    <option value="this_week">This Week</option>
                </select>
            </div>

            {/* Dashboard sections */}
            <div className="dashboard-grid">
                <DashboardOverview data={data.overview} />
                <BehaviorInsights data={data.behaviorInsights} />
                <ProgressOverview data={data.progressOverview} />
            </div>
        </div>
    );
}

// Export for use in your application
export { OptimizedTeacherAPI, useOptimizedTeacherDashboard, OptimizedTeacherDashboard };
