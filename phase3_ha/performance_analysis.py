"""
Phase 3: Performance Analysis Module

Collects and analyzes performance metrics for the gRPC rendering service:
- Throughput (requests/second) with dip detection during failures
- Latency (p50, p95, p99) with spike detection
- Recovery time measurement after failures
- Automatic graph generation with failure/recovery annotations

Output:
- CSV files for all metrics
- PNG graphs with annotated failure points
- Summary statistics

Usage:
    python performance_analysis.py --duration 120 --rate 30
"""

import os
import sys
import time
import json
import csv
import logging
import threading
import statistics
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
from concurrent import futures

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import grpc
import rendering_service_pb2
import rendering_service_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import matplotlib for graphs
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available. Install with: pip install matplotlib")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class RequestEvent:
    """Single request event with timing."""
    request_id: int
    timestamp: float  # Unix timestamp when request was sent
    latency_ms: float  # Response time in milliseconds
    success: bool
    replica_id: str
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'request_id': self.request_id,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'latency_ms': self.latency_ms,
            'success': self.success,
            'replica_id': self.replica_id,
            'error_message': self.error_message
        }


@dataclass
class FailureEvent:
    """Records a failure and recovery event."""
    failure_id: int
    failure_timestamp: float
    recovery_timestamp: Optional[float] = None
    failed_replica: str = ""
    recovered_replica: str = ""
    requests_during_failure: int = 0
    
    @property
    def recovery_time_seconds(self) -> Optional[float]:
        if self.recovery_timestamp:
            return self.recovery_timestamp - self.failure_timestamp
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'failure_id': self.failure_id,
            'failure_timestamp': self.failure_timestamp,
            'failure_datetime': datetime.fromtimestamp(self.failure_timestamp).isoformat(),
            'recovery_timestamp': self.recovery_timestamp,
            'recovery_datetime': datetime.fromtimestamp(self.recovery_timestamp).isoformat() if self.recovery_timestamp else None,
            'recovery_time_seconds': self.recovery_time_seconds,
            'failed_replica': self.failed_replica,
            'recovered_replica': self.recovered_replica,
            'requests_during_failure': self.requests_during_failure
        }


@dataclass
class WindowMetrics:
    """Metrics for a time window (1 second)."""
    window_start: float
    window_end: float
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    latencies: List[float] = field(default_factory=list)
    
    @property
    def throughput(self) -> float:
        """Requests per second."""
        duration = self.window_end - self.window_start
        if duration > 0:
            return self.request_count / duration
        return 0.0
    
    @property
    def success_rate(self) -> float:
        if self.request_count > 0:
            return self.success_count / self.request_count
        return 0.0
    
    @property
    def p50_latency(self) -> float:
        if self.latencies:
            sorted_lat = sorted(self.latencies)
            idx = int(len(sorted_lat) * 0.50)
            return sorted_lat[min(idx, len(sorted_lat)-1)]
        return 0.0
    
    @property
    def p95_latency(self) -> float:
        if self.latencies:
            sorted_lat = sorted(self.latencies)
            idx = int(len(sorted_lat) * 0.95)
            return sorted_lat[min(idx, len(sorted_lat)-1)]
        return 0.0
    
    @property
    def p99_latency(self) -> float:
        if self.latencies:
            sorted_lat = sorted(self.latencies)
            idx = int(len(sorted_lat) * 0.99)
            return sorted_lat[min(idx, len(sorted_lat)-1)]
        return 0.0
    
    @property
    def avg_latency(self) -> float:
        if self.latencies:
            return statistics.mean(self.latencies)
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'window_start': self.window_start,
            'window_end': self.window_end,
            'datetime': datetime.fromtimestamp(self.window_start).isoformat(),
            'elapsed_seconds': 0,  # Will be set by analyzer
            'request_count': self.request_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'throughput_rps': self.throughput,
            'success_rate': self.success_rate,
            'avg_latency_ms': self.avg_latency,
            'p50_latency_ms': self.p50_latency,
            'p95_latency_ms': self.p95_latency,
            'p99_latency_ms': self.p99_latency
        }


# ============================================================================
# Load Generator
# ============================================================================

class LoadGenerator:
    """
    Generates continuous load against the gRPC rendering service.
    
    Features:
    - Adjustable request rate
    - Records all events with timestamps
    - Detects failures and recovery
    """
    
    def __init__(
        self,
        endpoints: List[str],
        target_rate: float = 30.0,  # requests per second
        timeout: float = 5.0
    ):
        self.endpoints = endpoints
        self.target_rate = target_rate
        self.timeout = timeout
        
        # Connection state
        self.current_endpoint_idx = 0
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[rendering_service_pb2_grpc.RenderingServiceStub] = None
        self.current_replica_id = ""
        
        # Event collection
        self.events: List[RequestEvent] = []
        self.failure_events: List[FailureEvent] = []
        self._events_lock = threading.Lock()
        
        # State tracking
        self._running = False
        self._in_failure_state = False
        self._current_failure: Optional[FailureEvent] = None
        self._failure_count = 0
        self._consecutive_failures = 0
        self._start_time: Optional[float] = None
        
    def connect(self, endpoint_idx: Optional[int] = None) -> bool:
        """Connect to a gRPC endpoint."""
        if endpoint_idx is not None:
            self.current_endpoint_idx = endpoint_idx
            
        endpoint = self.endpoints[self.current_endpoint_idx]
        
        try:
            if self.channel:
                self.channel.close()
                
            self.channel = grpc.insecure_channel(
                endpoint,
                options=[
                    ('grpc.keepalive_time_ms', 10000),
                    ('grpc.keepalive_timeout_ms', 5000),
                ]
            )
            self.stub = rendering_service_pb2_grpc.RenderingServiceStub(self.channel)
            
            # Test connection
            request = rendering_service_pb2.HealthCheckRequest(client_id="perf-analyzer")
            response = self.stub.HealthCheck(request, timeout=self.timeout)
            
            if response.healthy:
                self.current_replica_id = response.replica_id
                logger.info(f"Connected to {endpoint} (replica: {self.current_replica_id})")
                return True
                
        except Exception as e:
            logger.warning(f"Failed to connect to {endpoint}: {e}")
            
        return False
    
    def failover(self) -> bool:
        """Switch to next available endpoint."""
        original_idx = self.current_endpoint_idx
        
        for i in range(len(self.endpoints)):
            next_idx = (original_idx + 1 + i) % len(self.endpoints)
            if self.connect(next_idx):
                return True
        
        return False
    
    def send_request(self, request_id: int) -> RequestEvent:
        """Send a single request and record the event."""
        timestamp = time.time()
        
        try:
            request = rendering_service_pb2.RenderRequest(
                request_id=request_id,
                frame_number=request_id,
                width=1920,
                height=1080,
                timestamp=int(timestamp * 1000)
            )
            
            start_time = time.time()
            response = self.stub.RenderFrame(request, timeout=self.timeout)  # type: ignore
            latency_ms = (time.time() - start_time) * 1000
            
            event = RequestEvent(
                request_id=request_id,
                timestamp=timestamp,
                latency_ms=latency_ms,
                success=response.success,
                replica_id=response.replica_id
            )
            
            # Reset consecutive failures on success
            self._consecutive_failures = 0
            
            # Check for recovery from failure state
            if self._in_failure_state and self._current_failure:
                self._current_failure.recovery_timestamp = time.time()
                self._current_failure.recovered_replica = response.replica_id
                self._in_failure_state = False
                
                recovery_time = self._current_failure.recovery_time_seconds
                logger.info(f"RECOVERY detected! Time: {recovery_time:.2f}s, New replica: {response.replica_id}")
                
                with self._events_lock:
                    self.failure_events.append(self._current_failure)
                self._current_failure = None
            
            return event
            
        except grpc.RpcError as e:
            latency_ms = (time.time() - timestamp) * 1000
            
            self._consecutive_failures += 1
            
            # Detect failure state (3+ consecutive failures)
            if not self._in_failure_state and self._consecutive_failures >= 3:
                self._in_failure_state = True
                self._failure_count += 1
                self._current_failure = FailureEvent(
                    failure_id=self._failure_count,
                    failure_timestamp=timestamp,
                    failed_replica=self.current_replica_id
                )
                logger.warning(f"FAILURE detected! Replica: {self.current_replica_id}")
                
                # Try failover
                if self.failover():
                    logger.info(f"Failover initiated to {self.endpoints[self.current_endpoint_idx]}")
            
            if self._current_failure:
                self._current_failure.requests_during_failure += 1
            
            return RequestEvent(
                request_id=request_id,
                timestamp=timestamp,
                latency_ms=latency_ms,
                success=False,
                replica_id=self.current_replica_id,
                error_message=str(e)
            )
            
        except Exception as e:
            latency_ms = (time.time() - timestamp) * 1000
            return RequestEvent(
                request_id=request_id,
                timestamp=timestamp,
                latency_ms=latency_ms,
                success=False,
                replica_id=self.current_replica_id,
                error_message=str(e)
            )
    
    def run(self, duration_seconds: float = 60.0) -> List[RequestEvent]:
        """
        Run load generation for specified duration.
        
        Args:
            duration_seconds: How long to run (minimum 60 seconds recommended)
            
        Returns:
            List of all request events
        """
        logger.info("=" * 60)
        logger.info("LOAD GENERATOR STARTED")
        logger.info("=" * 60)
        logger.info(f"Target rate: {self.target_rate} req/sec")
        logger.info(f"Duration: {duration_seconds} seconds")
        logger.info(f"Endpoints: {self.endpoints}")
        logger.info("")
        
        # Connect to first endpoint
        if not self.connect():
            if not self.failover():
                logger.error("Could not connect to any endpoint!")
                return []
        
        self._running = True
        self._start_time = time.time()
        request_interval = 1.0 / self.target_rate
        request_id = 0
        
        end_time = self._start_time + duration_seconds
        last_status_time = self._start_time
        
        while time.time() < end_time and self._running:
            loop_start = time.time()
            
            # Send request
            event = self.send_request(request_id)
            
            with self._events_lock:
                self.events.append(event)
            
            request_id += 1
            
            # Status update every 10 seconds
            if time.time() - last_status_time >= 10.0:
                elapsed = time.time() - self._start_time
                actual_rate = request_id / elapsed
                success_count = sum(1 for e in self.events if e.success)
                success_rate = success_count / len(self.events) * 100 if self.events else 0
                
                logger.info(
                    f"Progress: {elapsed:.0f}s | "
                    f"Requests: {request_id} | "
                    f"Rate: {actual_rate:.1f}/s | "
                    f"Success: {success_rate:.1f}% | "
                    f"Failures: {self._failure_count}"
                )
                last_status_time = time.time()
            
            # Maintain target rate
            elapsed = time.time() - loop_start
            if elapsed < request_interval:
                time.sleep(request_interval - elapsed)
        
        self._running = False
        
        # Final unclosed failure
        if self._current_failure:
            with self._events_lock:
                self.failure_events.append(self._current_failure)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("LOAD GENERATION COMPLETE")
        logger.info("=" * 60)
        
        return self.events
    
    def stop(self):
        """Stop the load generator."""
        self._running = False
        if self.channel:
            self.channel.close()


# ============================================================================
# Performance Analyzer
# ============================================================================

class PerformanceAnalyzer:
    """
    Analyzes collected metrics and generates reports.
    """
    
    def __init__(self, events: List[RequestEvent], failure_events: List[FailureEvent], start_time: float):
        self.events = events
        self.failure_events = failure_events
        self.start_time = start_time
        self.window_metrics: List[WindowMetrics] = []
        
    def compute_window_metrics(self, window_size: float = 1.0) -> List[WindowMetrics]:
        """
        Compute metrics for each time window.
        
        Args:
            window_size: Window size in seconds (default 1 second)
        """
        if not self.events:
            return []
        
        min_time = min(e.timestamp for e in self.events)
        max_time = max(e.timestamp for e in self.events)
        
        windows = []
        current_start = min_time
        
        while current_start < max_time:
            current_end = current_start + window_size
            
            # Get events in this window
            window_events = [
                e for e in self.events
                if current_start <= e.timestamp < current_end
            ]
            
            if window_events:
                metrics = WindowMetrics(
                    window_start=current_start,
                    window_end=current_end,
                    request_count=len(window_events),
                    success_count=sum(1 for e in window_events if e.success),
                    failure_count=sum(1 for e in window_events if not e.success),
                    latencies=[e.latency_ms for e in window_events if e.success]
                )
            else:
                metrics = WindowMetrics(
                    window_start=current_start,
                    window_end=current_end
                )
            
            windows.append(metrics)
            current_start = current_end
        
        self.window_metrics = windows
        return windows
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get overall summary statistics."""
        if not self.events:
            return {}
        
        successful_events = [e for e in self.events if e.success]
        failed_events = [e for e in self.events if not e.success]
        
        all_latencies = [e.latency_ms for e in successful_events]
        
        duration = self.events[-1].timestamp - self.events[0].timestamp
        
        summary = {
            'total_requests': len(self.events),
            'successful_requests': len(successful_events),
            'failed_requests': len(failed_events),
            'success_rate_percent': len(successful_events) / len(self.events) * 100,
            'duration_seconds': duration,
            'overall_throughput_rps': len(self.events) / duration if duration > 0 else 0,
            'total_failures': len(self.failure_events),
        }
        
        if all_latencies:
            sorted_lat = sorted(all_latencies)
            summary.update({
                'avg_latency_ms': statistics.mean(all_latencies),
                'min_latency_ms': min(all_latencies),
                'max_latency_ms': max(all_latencies),
                'p50_latency_ms': sorted_lat[int(len(sorted_lat) * 0.50)],
                'p95_latency_ms': sorted_lat[int(len(sorted_lat) * 0.95)],
                'p99_latency_ms': sorted_lat[int(len(sorted_lat) * 0.99)],
                'stddev_latency_ms': statistics.stdev(all_latencies) if len(all_latencies) > 1 else 0
            })
        
        # Recovery times
        if self.failure_events:
            recovery_times = [
                f.recovery_time_seconds 
                for f in self.failure_events 
                if f.recovery_time_seconds is not None
            ]
            if recovery_times:
                summary['avg_recovery_time_seconds'] = statistics.mean(recovery_times)
                summary['min_recovery_time_seconds'] = min(recovery_times)
                summary['max_recovery_time_seconds'] = max(recovery_times)
        
        return summary
    
    def export_to_csv(self, output_dir: str = "."):
        """Export all metrics to CSV files."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export raw events
        events_file = os.path.join(output_dir, f"request_events_{timestamp}.csv")
        with open(events_file, 'w', newline='') as f:
            if self.events:
                writer = csv.DictWriter(f, fieldnames=self.events[0].to_dict().keys())
                writer.writeheader()
                for event in self.events:
                    writer.writerow(event.to_dict())
        logger.info(f"Exported request events to: {events_file}")
        
        # Export window metrics
        if self.window_metrics:
            metrics_file = os.path.join(output_dir, f"window_metrics_{timestamp}.csv")
            with open(metrics_file, 'w', newline='') as f:
                first_window = self.window_metrics[0]
                row = first_window.to_dict()
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()
                for i, window in enumerate(self.window_metrics):
                    row = window.to_dict()
                    row['elapsed_seconds'] = i  # Override with actual elapsed
                    writer.writerow(row)
            logger.info(f"Exported window metrics to: {metrics_file}")
        
        # Export failure events
        if self.failure_events:
            failures_file = os.path.join(output_dir, f"failure_events_{timestamp}.csv")
            with open(failures_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.failure_events[0].to_dict().keys())
                writer.writeheader()
                for event in self.failure_events:
                    writer.writerow(event.to_dict())
            logger.info(f"Exported failure events to: {failures_file}")
        
        # Export summary
        summary = self.get_summary_statistics()
        summary_file = os.path.join(output_dir, f"summary_{timestamp}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Exported summary to: {summary_file}")
        
        return timestamp
    
    def generate_graphs(self, output_dir: str = ".", timestamp: str = ""):
        """Generate performance graphs with failure annotations."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available, skipping graph generation")
            return
        
        if not self.window_metrics:
            self.compute_window_metrics()
        
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare data
        elapsed_seconds = list(range(len(self.window_metrics)))
        throughputs = [w.throughput for w in self.window_metrics]
        p95_latencies = [w.p95_latency if w.p95_latency > 0 else None for w in self.window_metrics]
        avg_latencies = [w.avg_latency if w.avg_latency > 0 else None for w in self.window_metrics]
        success_rates = [w.success_rate * 100 for w in self.window_metrics]
        
        # Failure/recovery points (in elapsed seconds from start)
        start_ts = self.window_metrics[0].window_start if self.window_metrics else 0
        failure_points = []
        recovery_points = []
        
        for f in self.failure_events:
            failure_sec = f.failure_timestamp - start_ts
            failure_points.append(failure_sec)
            if f.recovery_timestamp:
                recovery_sec = f.recovery_timestamp - start_ts
                recovery_points.append(recovery_sec)
        
        # Create figure with subplots
        fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
        fig.suptitle('Phase 3: Performance Analysis - gRPC Rendering Service', fontsize=14, fontweight='bold')
        
        # ---- Graph 1: Throughput vs Time ----
        ax1 = axes[0]
        ax1.plot(elapsed_seconds, throughputs, 'b-', linewidth=1.5, label='Throughput')
        ax1.fill_between(elapsed_seconds, throughputs, alpha=0.3)
        ax1.set_ylabel('Throughput (req/sec)', fontsize=11)
        ax1.set_title('Throughput vs Time', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right')
        
        # Annotate failures
        for i, fp in enumerate(failure_points):
            if 0 <= fp <= max(elapsed_seconds):
                ax1.axvline(x=fp, color='red', linestyle='--', linewidth=2, alpha=0.8)
                ax1.annotate(f'FAILURE {i+1}', xy=(fp, ax1.get_ylim()[1]*0.9),
                            fontsize=9, color='red', fontweight='bold',
                            rotation=90, va='top')
        
        for i, rp in enumerate(recovery_points):
            if 0 <= rp <= max(elapsed_seconds):
                ax1.axvline(x=rp, color='green', linestyle='--', linewidth=2, alpha=0.8)
                ax1.annotate(f'RECOVERY {i+1}', xy=(rp, ax1.get_ylim()[1]*0.7),
                            fontsize=9, color='green', fontweight='bold',
                            rotation=90, va='top')
        
        # ---- Graph 2: Latency vs Time ----
        ax2 = axes[1]
        
        # Filter None values for plotting
        valid_p95 = [(x, y) for x, y in zip(elapsed_seconds, p95_latencies) if y is not None]
        valid_avg = [(x, y) for x, y in zip(elapsed_seconds, avg_latencies) if y is not None]
        
        if valid_p95:
            ax2.plot([x for x, y in valid_p95], [y for x, y in valid_p95], 
                    'r-', linewidth=1.5, label='P95 Latency')
        if valid_avg:
            ax2.plot([x for x, y in valid_avg], [y for x, y in valid_avg], 
                    'b-', linewidth=1.5, label='Avg Latency', alpha=0.7)
        
        ax2.set_ylabel('Latency (ms)', fontsize=11)
        ax2.set_title('Latency vs Time (P95 and Average)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right')
        
        # Annotate failures
        for i, fp in enumerate(failure_points):
            if 0 <= fp <= max(elapsed_seconds):
                ax2.axvline(x=fp, color='red', linestyle='--', linewidth=2, alpha=0.8)
        for i, rp in enumerate(recovery_points):
            if 0 <= rp <= max(elapsed_seconds):
                ax2.axvline(x=rp, color='green', linestyle='--', linewidth=2, alpha=0.8)
        
        # ---- Graph 3: Success Rate vs Time ----
        ax3 = axes[2]
        ax3.plot(elapsed_seconds, success_rates, 'g-', linewidth=1.5, label='Success Rate')
        ax3.fill_between(elapsed_seconds, success_rates, alpha=0.3, color='green')
        ax3.set_ylabel('Success Rate (%)', fontsize=11)
        ax3.set_xlabel('Time (seconds)', fontsize=11)
        ax3.set_title('Success Rate vs Time', fontsize=12)
        ax3.set_ylim(0, 105)
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='lower right')
        
        # Annotate failures
        for i, fp in enumerate(failure_points):
            if 0 <= fp <= max(elapsed_seconds):
                ax3.axvline(x=fp, color='red', linestyle='--', linewidth=2, alpha=0.8)
        for i, rp in enumerate(recovery_points):
            if 0 <= rp <= max(elapsed_seconds):
                ax3.axvline(x=rp, color='green', linestyle='--', linewidth=2, alpha=0.8)
        
        plt.tight_layout()
        
        # Save graph
        graph_file = os.path.join(output_dir, f"performance_graphs_{timestamp}.png")
        plt.savefig(graph_file, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved performance graphs to: {graph_file}")
        
        # ---- Additional: Recovery Time Bar Chart ----
        if self.failure_events:
            fig2, ax = plt.subplots(figsize=(10, 6))
            
            recovery_times = []
            labels = []
            for f in self.failure_events:
                if f.recovery_time_seconds is not None:
                    recovery_times.append(f.recovery_time_seconds)
                    labels.append(f"Failure {f.failure_id}\n{f.failed_replica}")
            
            if recovery_times:
                bars = ax.bar(labels, recovery_times, color=['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4'])
                ax.set_ylabel('Recovery Time (seconds)', fontsize=11)
                ax.set_xlabel('Failure Event', fontsize=11)
                ax.set_title('Recovery Time per Failure Event', fontsize=12)
                ax.grid(True, axis='y', alpha=0.3)
                
                # Add value labels on bars
                for bar, val in zip(bars, recovery_times):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                           f'{val:.2f}s', ha='center', va='bottom', fontsize=10)
                
                recovery_graph = os.path.join(output_dir, f"recovery_times_{timestamp}.png")
                plt.savefig(recovery_graph, dpi=150, bbox_inches='tight')
                plt.close()
                logger.info(f"Saved recovery time graph to: {recovery_graph}")


# ============================================================================
# Main Entry Point
# ============================================================================

def run_performance_analysis(
    endpoints: List[str] = ['localhost:50051', 'localhost:50052'],
    duration: float = 60.0,
    rate: float = 30.0,
    output_dir: str = "performance_results"
):
    """
    Run complete performance analysis.
    
    Args:
        endpoints: gRPC server endpoints
        duration: Test duration in seconds
        rate: Target request rate per second
        output_dir: Directory for output files
    """
    print()
    print("=" * 70)
    print("  PHASE 3: PERFORMANCE ANALYSIS")
    print("  gRPC Rendering Service with Failover")
    print("=" * 70)
    print()
    print(f"  Endpoints:    {endpoints}")
    print(f"  Duration:     {duration} seconds")
    print(f"  Target Rate:  {rate} requests/second")
    print(f"  Output Dir:   {output_dir}")
    print()
    print("  Instructions:")
    print("  - The load generator will send continuous requests")
    print("  - CLOSE THE RENDERER WINDOW to trigger a failure")
    print("  - Watch the failover and recovery in real-time")
    print("  - Metrics and graphs will be generated at the end")
    print()
    print("-" * 70)
    print()
    
    # Create load generator
    generator = LoadGenerator(
        endpoints=endpoints,
        target_rate=rate,
        timeout=5.0
    )
    
    try:
        # Run load generation
        start_time = time.time()
        events = generator.run(duration_seconds=duration)
        
        if not events:
            logger.error("No events collected!")
            return
        
        # Analyze results
        logger.info("Analyzing performance data...")
        analyzer = PerformanceAnalyzer(
            events=events,
            failure_events=generator.failure_events,
            start_time=start_time
        )
        
        # Compute window metrics
        analyzer.compute_window_metrics(window_size=1.0)
        
        # Export data
        timestamp = analyzer.export_to_csv(output_dir)
        
        # Generate graphs
        analyzer.generate_graphs(output_dir, timestamp)
        
        # Print summary
        summary = analyzer.get_summary_statistics()
        
        print()
        print("=" * 70)
        print("  PERFORMANCE SUMMARY")
        print("=" * 70)
        print()
        print(f"  Total Requests:      {summary.get('total_requests', 0)}")
        print(f"  Successful:          {summary.get('successful_requests', 0)}")
        print(f"  Failed:              {summary.get('failed_requests', 0)}")
        print(f"  Success Rate:        {summary.get('success_rate_percent', 0):.2f}%")
        print()
        print(f"  Duration:            {summary.get('duration_seconds', 0):.2f} seconds")
        print(f"  Throughput:          {summary.get('overall_throughput_rps', 0):.2f} req/sec")
        print()
        print(f"  Avg Latency:         {summary.get('avg_latency_ms', 0):.2f} ms")
        print(f"  P50 Latency:         {summary.get('p50_latency_ms', 0):.2f} ms")
        print(f"  P95 Latency:         {summary.get('p95_latency_ms', 0):.2f} ms")
        print(f"  P99 Latency:         {summary.get('p99_latency_ms', 0):.2f} ms")
        print()
        print(f"  Total Failures:      {summary.get('total_failures', 0)}")
        
        if 'avg_recovery_time_seconds' in summary:
            print(f"  Avg Recovery Time:   {summary.get('avg_recovery_time_seconds', 0):.2f} seconds")
            print(f"  Min Recovery Time:   {summary.get('min_recovery_time_seconds', 0):.2f} seconds")
            print(f"  Max Recovery Time:   {summary.get('max_recovery_time_seconds', 0):.2f} seconds")
        
        print()
        print(f"  Output files saved to: {os.path.abspath(output_dir)}/")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        generator.stop()
    finally:
        generator.stop()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance Analysis for gRPC Rendering Service')
    parser.add_argument('--endpoints', nargs='+',
                       default=['localhost:50051', 'localhost:50052'],
                       help='gRPC server endpoints')
    parser.add_argument('--duration', type=float, default=60.0,
                       help='Test duration in seconds (minimum 60 recommended)')
    parser.add_argument('--rate', type=float, default=30.0,
                       help='Target request rate per second')
    parser.add_argument('--output', type=str, default='performance_results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    run_performance_analysis(
        endpoints=args.endpoints,
        duration=args.duration,
        rate=args.rate,
        output_dir=args.output
    )


if __name__ == '__main__':
    main()
