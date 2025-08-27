"""
Performance analytics API routes for admin dashboard.

Provides detailed performance metrics including:
- Response time metrics and percentiles
- Query throughput analysis  
- Timeline data for charts
- Error rate tracking
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class PerformanceMetrics(BaseModel):
    """Model for performance metrics response."""

    response_time: dict
    throughput: dict
    error_rate: dict
    cache_hit_rate: dict


class TimelinePoint(BaseModel):
    """Model for timeline data point."""

    timestamp: str
    avg_response_time: float
    query_count: int
    error_rate: float
    cache_hit_rate: float


class PerformanceTimeline(BaseModel):
    """Model for performance timeline response."""

    timeline: List[TimelinePoint]


class PercentileMetrics(BaseModel):
    """Model for response time percentiles."""

    p50: float
    p95: float
    p99: float


# Database connection utility imported from shared module
from ..core.database_utils import get_rag_monitoring_db_connection as get_db_connection


def parse_time_range(time_range: str) -> tuple:
    """Parse time range string to start and end dates."""
    end_date = datetime.now()

    if time_range == "1h":
        start_date = end_date - timedelta(hours=1)
    elif time_range == "6h":
        start_date = end_date - timedelta(hours=6)
    elif time_range == "24h":
        start_date = end_date - timedelta(hours=24)
    elif time_range == "7d":
        start_date = end_date - timedelta(days=7)
    elif time_range == "30d":
        start_date = end_date - timedelta(days=30)
    else:
        # Default to 24 hours
        start_date = end_date - timedelta(hours=24)

    return start_date, end_date


@router.get("/performance/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    time_range: str = Query("24h", description="Time range for metrics (1h, 6h, 24h, 7d, 30d)")
):
    """Get performance metrics with current and previous period comparison."""
    try:
        conn = get_db_connection()

        if not conn:
            # Return empty metrics if database is not available
            return PerformanceMetrics(
                response_time={"current": 0, "previous": 0, "change": 0},
                throughput={"current": 0, "previous": 0, "change": 0},
                error_rate={"current": 0, "previous": 0, "change": 0},
                cache_hit_rate={"current": 85, "previous": 85, "change": 0},
            )

        cursor = conn.cursor()
        start_date, end_date = parse_time_range(time_range)

        # Check what data is available and adjust comparison period accordingly
        cursor.execute(
            """
            SELECT MIN(timestamp) as earliest_data, MAX(timestamp) as latest_data
            FROM query_logs
        """
        )
        result = cursor.fetchone()

        if not result or not result["earliest_data"]:
            # No data available
            return PerformanceMetrics(
                response_time={"current": 0, "previous": 0, "change": 0},
                throughput={"current": 0, "previous": 0, "change": 0},
                error_rate={"current": 0, "previous": 0, "change": 0},
                cache_hit_rate={"current": 85, "previous": 85, "change": 0},
            )

        # Calculate dynamic date ranges based on the period
        period_duration = end_date - start_date
        previous_period_end = start_date
        previous_period_start = previous_period_end - period_duration

        # Convert to string format for SQL queries
        current_period_start = start_date.isoformat()
        current_period_end = end_date.isoformat()
        previous_start = previous_period_start.isoformat()
        previous_end = previous_period_end.isoformat()

        # Get current period response time
        cursor.execute(
            """
            SELECT AVG(response_time_ms) as avg_response_time
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
            AND response_time_ms IS NOT NULL
        """,
            (current_period_start, current_period_end),
        )

        result = cursor.fetchone()
        current_response_time = result["avg_response_time"] if result and result["avg_response_time"] else 0.0

        # Get previous period response time
        cursor.execute(
            """
            SELECT AVG(response_time_ms) as avg_response_time
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
            AND response_time_ms IS NOT NULL
        """,
            (previous_start, previous_end),
        )

        result = cursor.fetchone()
        previous_response_time = result["avg_response_time"] if result and result["avg_response_time"] else 0.0

        # Calculate response time change
        response_time_change = 0.0
        if previous_response_time > 0:
            response_time_change = ((current_response_time - previous_response_time) / previous_response_time) * 100

        # Get current period throughput (queries per hour)
        cursor.execute(
            """
            SELECT COUNT(*) as query_count
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
        """,
            (current_period_start, current_period_end),
        )

        result = cursor.fetchone()
        current_queries = result["query_count"] if result else 0
        period_hours = (end_date - start_date).total_seconds() / 3600
        current_throughput = current_queries / period_hours if period_hours > 0 else 0

        # Get previous period throughput
        cursor.execute(
            """
            SELECT COUNT(*) as query_count
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
        """,
            (previous_start, previous_end),
        )

        result = cursor.fetchone()
        previous_queries = result["query_count"] if result else 0
        # Previous period has the same duration as current period
        previous_throughput = previous_queries / period_hours if period_hours > 0 else 0

        # Calculate throughput change
        throughput_change = 0.0
        if previous_throughput > 0:
            throughput_change = ((current_throughput - previous_throughput) / previous_throughput) * 100

        # Get current period error rate
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN error_occurred = 1 THEN 1 END) as errors
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
        """,
            (current_period_start, current_period_end),
        )

        result = cursor.fetchone()
        current_error_rate = 0.0
        if result and result["total"] > 0:
            current_error_rate = (result["errors"] / result["total"]) * 100

        # Get previous period error rate
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN error_occurred = 1 THEN 1 END) as errors
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
        """,
            (previous_start, previous_end),
        )

        result = cursor.fetchone()
        previous_error_rate = 0.0
        if result and result["total"] > 0:
            previous_error_rate = (result["errors"] / result["total"]) * 100

        # Calculate error rate change
        error_rate_change = current_error_rate - previous_error_rate

        conn.close()

        # Cache hit rate is a static value for now - could be enhanced later
        cache_hit_rate = 85.0

        return PerformanceMetrics(
            response_time={
                "current": round(current_response_time, 1),
                "previous": round(previous_response_time, 1),
                "change": round(response_time_change, 2),
            },
            throughput={
                "current": round(current_throughput, 1),
                "previous": round(previous_throughput, 1),
                "change": round(throughput_change, 2),
            },
            error_rate={
                "current": round(current_error_rate, 2),
                "previous": round(previous_error_rate, 2),
                "change": round(error_rate_change, 2),
            },
            cache_hit_rate={"current": cache_hit_rate, "previous": cache_hit_rate, "change": 0.0},
        )

    except sqlite3.Error as e:
        logger.error(f"Database error in get_performance_metrics: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error in get_performance_metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/performance/timeline", response_model=PerformanceTimeline)
async def get_performance_timeline(
    days: int = Query(7, ge=1, le=30, description="Number of days for timeline"),
    interval: str = Query("hour", description="Interval for timeline (hour, day)"),
):
    """Get performance timeline data for charts."""
    try:
        conn = get_db_connection()

        if not conn:
            # Return empty timeline if database is not available
            return PerformanceTimeline(timeline=[])

        cursor = conn.cursor()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Generate timeline based on interval
        if interval == "hour":
            # Group by hour
            cursor.execute(
                """
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as time_bucket,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(*) as query_count,
                    AVG(CASE WHEN error_occurred = 1 THEN 1 ELSE 0 END) as error_rate
                FROM query_logs
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY time_bucket
                ORDER BY time_bucket
            """,
                (start_date.isoformat(), end_date.isoformat()),
            )
        else:
            # Group by day
            cursor.execute(
                """
                SELECT 
                    strftime('%Y-%m-%d', timestamp) as time_bucket,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(*) as query_count,
                    AVG(CASE WHEN error_occurred = 1 THEN 1 ELSE 0 END) as error_rate
                FROM query_logs
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY time_bucket
                ORDER BY time_bucket
            """,
                (start_date.isoformat(), end_date.isoformat()),
            )

        results = cursor.fetchall()

        timeline_points = []
        for row in results:
            timeline_points.append(
                TimelinePoint(
                    timestamp=row["time_bucket"],
                    avg_response_time=row["avg_response_time"] or 0.0,
                    query_count=row["query_count"] or 0,
                    error_rate=(row["error_rate"] or 0.0) * 100,  # Convert to percentage
                    cache_hit_rate=85.0,  # Static value for now
                )
            )

        conn.close()

        return PerformanceTimeline(timeline=timeline_points)

    except sqlite3.Error as e:
        logger.error(f"Database error in get_performance_timeline: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error in get_performance_timeline: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/performance/percentiles", response_model=PercentileMetrics)
async def get_response_time_percentiles(
    time_range: str = Query("24h", description="Time range for percentiles (1h, 6h, 24h, 7d, 30d)")
):
    """Get response time percentiles."""
    try:
        conn = get_db_connection()

        if not conn:
            # Return empty percentiles if database is not available
            return PercentileMetrics(p50=0, p95=0, p99=0)

        cursor = conn.cursor()
        start_date, end_date = parse_time_range(time_range)

        # Get all response times for the period
        cursor.execute(
            """
            SELECT response_time_ms
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
            AND response_time_ms IS NOT NULL
            ORDER BY response_time_ms
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )

        response_times = [row["response_time_ms"] for row in cursor.fetchall()]

        conn.close()

        if not response_times:
            return PercentileMetrics(p50=0, p95=0, p99=0)

        # Calculate percentiles
        def get_percentile(data, percentile):
            if not data:
                return 0
            index = int((percentile / 100) * len(data)) - 1
            index = max(0, min(index, len(data) - 1))
            return data[index]

        p50 = get_percentile(response_times, 50)
        p95 = get_percentile(response_times, 95)
        p99 = get_percentile(response_times, 99)

        return PercentileMetrics(p50=round(p50, 1), p95=round(p95, 1), p99=round(p99, 1))

    except sqlite3.Error as e:
        logger.error(f"Database error in get_response_time_percentiles: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error in get_response_time_percentiles: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
