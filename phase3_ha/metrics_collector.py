"""
Phase 3: High Availability Rendering Service
Performance Metrics Collector and Visualizer

This module provides comprehensive metrics collection, analysis,
and visualization for the fault-tolerant rendering service.
"""

import time
import json
import csv
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import threading
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FrameMetricPoint:
    """Single metric point for a rendered frame."""
    timestamp: float
    elapsed_time: float
    frame_number: int
    latency_ms: float
    success: bool
    replica_id: str
    geometry_time_ms: float = 0.0
    lighting_time_ms: float = 0.0
    postprocess_time_ms: float = 0.0
    error: str = ""


@dataclass
class TimeWindowStats:
    """Statistics for a time window."""
    window_start: float
    window_end: float
    request_count: int
    success_count: int
    failure_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_rps: float


@dataclass
class FailureEvent:
    """Record of a failure event."""
    timestamp: float
    elapsed_time: float
    event_type: str
    replica_id: str
    message: str
    recovery_time: float = 0.0


class MetricsCollector:
    """
    Collects and aggregates performance metrics from the rendering service.
    
    Features:
    - Real-time metric collection
    - Time-windowed statistics (1s, 5s, 30s, 60s)
    - Failure event tracking
    - Recovery time calculation
    - Export to JSON/CSV for analysis
    """
    
    def __init__(self, window_sizes: Optional[List[float]] = None):
        if window_sizes is None:
            window_sizes = [1.0, 5.0, 30.0, 60.0]
        
        self.window_sizes = window_sizes
        self.metrics: deque = deque(maxlen=1000000)
        self.failure_events: List[FailureEvent] = []
        self.start_time: float = time.time()
        self._lock = threading.Lock()
        
        # Track recovery
        self._last_failure_time: Dict[str, float] = {}
        self._failure_active: Dict[str, bool] = {}
    
    def record_frame(
        self,
        frame_number: int,
        latency_ms: float,
        success: bool,
        replica_id: str,
        geometry_time_ms: float = 0.0,
        lighting_time_ms: float = 0.0,
        postprocess_time_ms: float = 0.0,
        error: str = ""
    ):
        """Record metrics for a rendered frame."""
        now = time.time()
        elapsed = now - self.start_time
        
        metric = FrameMetricPoint(
            timestamp=now,
            elapsed_time=elapsed,
            frame_number=frame_number,
            latency_ms=latency_ms,
            success=success,
            replica_id=replica_id,
            geometry_time_ms=geometry_time_ms,
            lighting_time_ms=lighting_time_ms,
            postprocess_time_ms=postprocess_time_ms,
            error=error
        )
        
        with self._lock:
            self.metrics.append(metric)
            
            # Track failure/recovery
            if not success:
                if not self._failure_active.get(replica_id, False):
                    self._failure_active[replica_id] = True
                    self._last_failure_time[replica_id] = now
            else:
                if self._failure_active.get(replica_id, False):
                    # Recovery detected
                    recovery_time = now - self._last_failure_time.get(replica_id, now)
                    self._failure_active[replica_id] = False
                    
                    self.failure_events.append(FailureEvent(
                        timestamp=self._last_failure_time.get(replica_id, now),
                        elapsed_time=self._last_failure_time.get(replica_id, now) - self.start_time,
                        event_type="RECOVERED",
                        replica_id=replica_id,
                        message=f"Recovered after {recovery_time:.2f}s",
                        recovery_time=recovery_time
                    ))
    
    def record_failure_event(
        self,
        event_type: str,
        replica_id: str,
        message: str
    ):
        """Record a failure event (crash, timeout, etc.)."""
        now = time.time()
        elapsed = now - self.start_time
        
        event = FailureEvent(
            timestamp=now,
            elapsed_time=elapsed,
            event_type=event_type,
            replica_id=replica_id,
            message=message
        )
        
        with self._lock:
            self.failure_events.append(event)
            self._failure_active[replica_id] = True
            self._last_failure_time[replica_id] = now
    
    def get_window_stats(self, window_size: float) -> TimeWindowStats:
        """Get statistics for the last N seconds."""
        now = time.time()
        window_start = now - window_size
        
        with self._lock:
            # Filter metrics in window
            window_metrics = [
                m for m in self.metrics
                if m.timestamp >= window_start
            ]
        
        if not window_metrics:
            return TimeWindowStats(
                window_start=window_start,
                window_end=now,
                request_count=0,
                success_count=0,
                failure_count=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                throughput_rps=0
            )
        
        successful = [m for m in window_metrics if m.success]
        latencies = [m.latency_ms for m in successful]
        
        if latencies:
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            avg_latency = statistics.mean(latencies)
            p50 = sorted_latencies[int(n * 0.50)]
            p95 = sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1]
            p99 = sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]
            min_lat = min(latencies)
            max_lat = max(latencies)
        else:
            avg_latency = p50 = p95 = p99 = min_lat = max_lat = 0
        
        return TimeWindowStats(
            window_start=window_start,
            window_end=now,
            request_count=len(window_metrics),
            success_count=len(successful),
            failure_count=len(window_metrics) - len(successful),
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            min_latency_ms=min_lat,
            max_latency_ms=max_lat,
            throughput_rps=len(successful) / window_size
        )
    
    def get_all_window_stats(self) -> Dict[float, TimeWindowStats]:
        """Get statistics for all configured window sizes."""
        return {ws: self.get_window_stats(ws) for ws in self.window_sizes}
    
    def get_time_series(self, bucket_size: float = 1.0) -> List[Dict]:
        """Get time series data bucketed by time."""
        with self._lock:
            if not self.metrics:
                return []
            
            metrics_list = list(self.metrics)
        
        if not metrics_list:
            return []
        
        min_time = metrics_list[0].elapsed_time
        max_time = metrics_list[-1].elapsed_time
        
        buckets = []
        current_time = 0
        
        while current_time <= max_time:
            bucket_end = current_time + bucket_size
            
            bucket_metrics = [
                m for m in metrics_list
                if current_time <= m.elapsed_time < bucket_end
            ]
            
            if bucket_metrics:
                successful = [m for m in bucket_metrics if m.success]
                latencies = [m.latency_ms for m in successful]
                
                buckets.append({
                    'time': current_time,
                    'time_end': bucket_end,
                    'request_count': len(bucket_metrics),
                    'success_count': len(successful),
                    'failure_count': len(bucket_metrics) - len(successful),
                    'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
                    'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 20 else (max(latencies) if latencies else 0),
                    'throughput_rps': len(successful) / bucket_size
                })
            else:
                buckets.append({
                    'time': current_time,
                    'time_end': bucket_end,
                    'request_count': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'avg_latency_ms': 0,
                    'p95_latency_ms': 0,
                    'throughput_rps': 0
                })
            
            current_time = bucket_end
        
        return buckets
    
    def get_summary(self) -> Dict:
        """Get overall summary statistics."""
        with self._lock:
            all_metrics = list(self.metrics)
            all_events = list(self.failure_events)
        
        if not all_metrics:
            return {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'success_rate': 0,
                'total_duration': time.time() - self.start_time,
                'avg_latency_ms': 0,
                'p50_latency_ms': 0,
                'p95_latency_ms': 0,
                'p99_latency_ms': 0,
                'throughput_rps': 0,
                'failure_events': len(all_events),
                'avg_recovery_time': 0
            }
        
        successful = [m for m in all_metrics if m.success]
        latencies = [m.latency_ms for m in successful]
        
        duration = time.time() - self.start_time
        
        if latencies:
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            avg_latency = statistics.mean(latencies)
            p50 = sorted_latencies[int(n * 0.50)]
            p95 = sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1]
            p99 = sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]
        else:
            avg_latency = p50 = p95 = p99 = 0
        
        recovery_times = [e.recovery_time for e in all_events if e.recovery_time > 0]
        avg_recovery = statistics.mean(recovery_times) if recovery_times else 0
        
        return {
            'total_requests': len(all_metrics),
            'successful_requests': len(successful),
            'failed_requests': len(all_metrics) - len(successful),
            'success_rate': len(successful) / len(all_metrics) if all_metrics else 0,
            'total_duration': duration,
            'avg_latency_ms': avg_latency,
            'p50_latency_ms': p50,
            'p95_latency_ms': p95,
            'p99_latency_ms': p99,
            'throughput_rps': len(successful) / duration if duration > 0 else 0,
            'failure_events': len(all_events),
            'avg_recovery_time': avg_recovery
        }
    
    def export_json(self, filepath: str):
        """Export all metrics to JSON."""
        with self._lock:
            data = {
                'start_time': self.start_time,
                'export_time': time.time(),
                'summary': self.get_summary(),
                'time_series': self.get_time_series(),
                'failure_events': [asdict(e) for e in self.failure_events],
                'raw_metrics': [asdict(m) for m in self.metrics]
            }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Metrics exported to {filepath}")
    
    def export_csv(self, filepath: str):
        """Export metrics to CSV for plotting."""
        with self._lock:
            metrics_list = list(self.metrics)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'elapsed_time', 'frame_number', 'latency_ms',
                'success', 'replica_id', 'geometry_time_ms', 'lighting_time_ms',
                'postprocess_time_ms', 'error'
            ])
            
            for m in metrics_list:
                writer.writerow([
                    m.timestamp, m.elapsed_time, m.frame_number, m.latency_ms,
                    m.success, m.replica_id, m.geometry_time_ms, m.lighting_time_ms,
                    m.postprocess_time_ms, m.error
                ])
        
        logger.info(f"CSV exported to {filepath}")
    
    def export_time_series_csv(self, filepath: str, bucket_size: float = 1.0):
        """Export time series data to CSV for plotting."""
        time_series = self.get_time_series(bucket_size)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'time', 'request_count', 'success_count', 'failure_count',
                'avg_latency_ms', 'p95_latency_ms', 'throughput_rps'
            ])
            
            for bucket in time_series:
                writer.writerow([
                    bucket['time'], bucket['request_count'], bucket['success_count'],
                    bucket['failure_count'], bucket['avg_latency_ms'],
                    bucket['p95_latency_ms'], bucket['throughput_rps']
                ])
        
        logger.info(f"Time series CSV exported to {filepath}")
    
    def export_failure_events_csv(self, filepath: str):
        """Export failure events to CSV."""
        with self._lock:
            events = list(self.failure_events)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'elapsed_time', 'event_type', 'replica_id',
                'message', 'recovery_time'
            ])
            
            for e in events:
                writer.writerow([
                    e.timestamp, e.elapsed_time, e.event_type, e.replica_id,
                    e.message, e.recovery_time
                ])
        
        logger.info(f"Failure events CSV exported to {filepath}")


def generate_performance_report(collector: MetricsCollector, output_dir: str):
    """Generate a comprehensive performance report."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Export all data
    collector.export_json(os.path.join(output_dir, 'full_metrics.json'))
    collector.export_csv(os.path.join(output_dir, 'raw_metrics.csv'))
    collector.export_time_series_csv(os.path.join(output_dir, 'time_series.csv'))
    collector.export_failure_events_csv(os.path.join(output_dir, 'failure_events.csv'))
    
    # Generate summary report
    summary = collector.get_summary()
    
    report = f"""
================================================================================
                    PERFORMANCE ANALYSIS REPORT
================================================================================
Generated: {datetime.now().isoformat()}
Test Duration: {summary['total_duration']:.1f} seconds

OVERVIEW
--------------------------------------------------------------------------------
Total Requests:     {summary['total_requests']}
Successful:         {summary['successful_requests']}
Failed:             {summary['failed_requests']}
Success Rate:       {summary['success_rate']*100:.2f}%
Throughput:         {summary['throughput_rps']:.2f} req/sec

LATENCY METRICS
--------------------------------------------------------------------------------
Average:            {summary['avg_latency_ms']:.2f} ms
P50 (Median):       {summary['p50_latency_ms']:.2f} ms
P95:                {summary['p95_latency_ms']:.2f} ms
P99:                {summary['p99_latency_ms']:.2f} ms

FAULT TOLERANCE
--------------------------------------------------------------------------------
Failure Events:     {summary['failure_events']}
Avg Recovery Time:  {summary['avg_recovery_time']:.2f} seconds

WINDOW STATISTICS
--------------------------------------------------------------------------------
"""
    
    for window_size, stats in collector.get_all_window_stats().items():
        report += f"""
{window_size}s Window:
  Requests: {stats.request_count}, Success: {stats.success_count}, Failed: {stats.failure_count}
  Avg Latency: {stats.avg_latency_ms:.2f}ms, P95: {stats.p95_latency_ms:.2f}ms
  Throughput: {stats.throughput_rps:.2f} req/sec
"""
    
    report += """
================================================================================
Files Generated:
  - full_metrics.json: Complete metrics data
  - raw_metrics.csv: Individual frame metrics
  - time_series.csv: Aggregated time series (1s buckets)
  - failure_events.csv: Failure and recovery events
================================================================================
"""
    
    report_path = os.path.join(output_dir, 'performance_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(report)
    logger.info(f"Performance report saved to {report_path}")


if __name__ == '__main__':
    # Demo/test the metrics collector
    collector = MetricsCollector()
    
    # Simulate some metrics
    import random
    for i in range(100):
        success = random.random() > 0.05
        latency = random.gauss(30, 10) if success else 0
        collector.record_frame(
            frame_number=i,
            latency_ms=max(0, latency),
            success=success,
            replica_id=f"replica-{random.randint(1, 2)}",
            geometry_time_ms=random.uniform(5, 15),
            lighting_time_ms=random.uniform(8, 20),
            postprocess_time_ms=random.uniform(3, 10)
        )
        time.sleep(0.05)
    
    # Generate report
    generate_performance_report(collector, 'test_metrics_output')
