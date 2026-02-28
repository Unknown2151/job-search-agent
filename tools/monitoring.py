"""
Production monitoring and health check utilities.
Tracks search performance, failure rates, and triggers alerts.
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
from config import MAX_CONSECUTIVE_FAILURES, FAILURE_RATE_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class SearchMetrics:
    """Tracks metrics for a single search operation."""
    query: str
    platform: str
    success: bool
    timestamp: datetime
    duration_seconds: float
    error_message: Optional[str] = None
    retry_count: int = 0


class PerformanceMonitor:
    """Monitors search performance and detects anomalies."""

    def __init__(self, window_size: int = 100):
        """Initialize performance monitor with a rolling window."""
        self.metrics: deque = deque(maxlen=window_size)
        self.consecutive_failures = 0
        self.last_alert: Dict[str, datetime] = {}

    def record_search(
        self,
        query: str,
        platform: str,
        success: bool,
        duration_seconds: float,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> None:
        """Record a search operation metric."""
        metric = SearchMetrics(
            query=query,
            platform=platform,
            success=success,
            timestamp=datetime.now(),
            duration_seconds=duration_seconds,
            error_message=error_message,
            retry_count=retry_count
        )
        self.metrics.append(metric)

        # Update consecutive failure counter
        if success:
            self.consecutive_failures = 0
            logger.info(f"Search succeeded: {platform} for '{query}' took {duration_seconds:.2f}s")
        else:
            self.consecutive_failures += 1
            logger.warning(
                f"Search failed: {platform} for '{query}' (attempt {retry_count + 1}). "
                f"Error: {error_message}"
            )

        # Check for anomalies
        self._check_anomalies()

    def _check_anomalies(self) -> None:
        """Check for performance anomalies and trigger alerts."""
        # Check consecutive failures
        if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            if not self._should_throttle_alert("consecutive_failures"):
                logger.error(
                    f"ALERT: {self.consecutive_failures} consecutive search failures detected. "
                    "Investigation required."
                )
                self.last_alert["consecutive_failures"] = datetime.now()

        # Check failure rate
        if len(self.metrics) >= 10:
            recent_metrics = list(self.metrics)[-10:]
            failure_rate = sum(1 for m in recent_metrics if not m.success) / len(recent_metrics)

            if failure_rate >= FAILURE_RATE_THRESHOLD:
                if not self._should_throttle_alert("failure_rate"):
                    logger.error(
                        f"ALERT: High failure rate detected ({failure_rate*100:.1f}%). "
                        "Check search tool health."
                    )
                    self.last_alert["failure_rate"] = datetime.now()

        # Check slow searches
        if len(self.metrics) >= 5:
            recent_metrics = list(self.metrics)[-5:]
            avg_duration = sum(m.duration_seconds for m in recent_metrics) / len(recent_metrics)
            max_duration = max(m.duration_seconds for m in recent_metrics)

            if max_duration > 60:  # Searches taking > 60 seconds
                if not self._should_throttle_alert("slow_searches"):
                    logger.warning(
                        f"ALERT: Slow searches detected. Max: {max_duration:.2f}s, "
                        f"Average: {avg_duration:.2f}s"
                    )
                    self.last_alert["slow_searches"] = datetime.now()

    def _should_throttle_alert(self, alert_type: str) -> bool:
        """Throttle repeated alerts to avoid spam (only alert every 5 minutes)."""
        if alert_type not in self.last_alert:
            return False

        last_time = self.last_alert[alert_type]
        return datetime.now() - last_time < timedelta(minutes=5)

    def get_summary(self) -> Dict:
        """Get summary statistics of recent searches."""
        if not self.metrics:
            return {"status": "no_data"}

        metrics_list = list(self.metrics)
        successful = sum(1 for m in metrics_list if m.success)
        failed = len(metrics_list) - successful

        if metrics_list:
            avg_duration = sum(m.duration_seconds for m in metrics_list) / len(metrics_list)
            max_duration = max(m.duration_seconds for m in metrics_list)
            min_duration = min(m.duration_seconds for m in metrics_list)
        else:
            avg_duration = max_duration = min_duration = 0

        return {
            "total_searches": len(metrics_list),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(metrics_list) if metrics_list else 0,
            "avg_duration_seconds": avg_duration,
            "max_duration_seconds": max_duration,
            "min_duration_seconds": min_duration,
            "consecutive_failures": self.consecutive_failures
        }

    def get_platform_stats(self) -> Dict[str, Dict]:
        """Get platform-specific statistics."""
        stats = {}

        for metric in self.metrics:
            if metric.platform not in stats:
                stats[metric.platform] = {"successful": 0, "failed": 0}

            if metric.success:
                stats[metric.platform]["successful"] += 1
            else:
                stats[metric.platform]["failed"] += 1

        # Add success rates
        for platform, data in stats.items():
            total = data["successful"] + data["failed"]
            data["success_rate"] = data["successful"] / total if total > 0 else 0

        return stats


# Global monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def record_search_metric(
    query: str,
    platform: str,
    success: bool,
    duration_seconds: float,
    error_message: Optional[str] = None,
    retry_count: int = 0
) -> None:
    """Convenience function to record a search metric."""
    monitor = get_monitor()
    monitor.record_search(query, platform, success, duration_seconds, error_message, retry_count)
