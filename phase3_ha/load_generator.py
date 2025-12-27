"""
Phase 3: High Availability Rendering Service
Load Generator - Continuous Input Generator for Performance Testing

This module simulates continuous rendering requests to test the
fault tolerance and performance of the rendering service.
"""

import time
import threading
import logging
import sys
import os
import json
import argparse
import random
import math
from datetime import datetime
from typing import Optional, List, Callable
from dataclasses import dataclass, field
from collections import deque
import signal

# Add the generated protobuf path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rendering_service_pb2
from rendering_client import RenderingClient, create_client
from replica_manager import ReplicaManager, HighAvailabilityClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LoadGeneratorConfig:
    """Configuration for the load generator."""
    duration_seconds: float = 60.0
    requests_per_second: float = 10.0
    ramp_up_seconds: float = 5.0
    ramp_down_seconds: float = 5.0
    frame_width: int = 320
    frame_height: int = 240
    camera_animation: bool = True
    inject_faults: bool = False
    fault_injection_time: float = 30.0
    output_file: str = "load_test_results.json"
    csv_output_file: str = "performance_metrics.csv"


@dataclass 
class LoadTestResult:
    """Results from a load test."""
    start_time: float
    end_time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_rps: float
    request_log: List[dict] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)


class LoadGenerator:
    """
    Generates continuous load for testing the rendering service.
    
    Features:
    - Configurable request rate
    - Ramp-up and ramp-down periods
    - Camera animation simulation
    - Fault injection support
    - Comprehensive metrics collection
    """
    
    def __init__(
        self,
        client: RenderingClient,
        config: LoadGeneratorConfig,
        fault_callback: Optional[Callable] = None
    ):
        self.client = client
        self.config = config
        self.fault_callback = fault_callback
        
        self._shutdown = threading.Event()
        self._paused = threading.Event()
        self._lock = threading.Lock()
        
        # Metrics
        self.request_count = 0
        self.successful_count = 0
        self.failed_count = 0
        self.latencies: List[float] = []
        self.request_log: deque = deque(maxlen=100000)
        self.events: List[dict] = []
        
        # Animation state
        self.camera_angle = 0.0
        self.camera_radius = 4.0
        
        # Timing
        self.start_time: float = 0
        self.end_time: float = 0
    
    def log_event(self, event_type: str, message: str):
        """Log an event with timestamp."""
        event = {
            'timestamp': time.time(),
            'elapsed': time.time() - self.start_time if self.start_time else 0,
            'event_type': event_type,
            'message': message
        }
        self.events.append(event)
        logger.info(f"[EVENT] {event_type}: {message}")
    
    def _generate_request(self, frame_number: int) -> rendering_service_pb2.RenderRequest:
        """Generate a render request with animated camera."""
        # Animate camera in a circle
        if self.config.camera_animation:
            self.camera_angle += 0.01
            cam_x = math.cos(self.camera_angle) * self.camera_radius
            cam_z = math.sin(self.camera_angle) * self.camera_radius
            cam_y = 1.0 + math.sin(self.camera_angle * 0.5) * 0.5
        else:
            cam_x, cam_y, cam_z = 0, 0, 4
        
        camera = rendering_service_pb2.CameraParams(
            position_x=cam_x,
            position_y=cam_y,
            position_z=cam_z,
            yaw=-90 + math.degrees(self.camera_angle),
            pitch=0,
            fov=45.0,
            aperture=16.0,
            shutter_speed=0.5,
            iso=1000.0
        )
        
        lighting = rendering_service_pb2.LightParams(
            point1_x=1.5,
            point1_y=0.75,
            point1_z=1.0,
            point1_radius=3.0,
            point_mode=True,
            ibl_mode=True
        )
        
        material = rendering_service_pb2.MaterialParams(
            roughness=0.01,
            metallicity=0.02,
            f0_r=0.04,
            f0_g=0.04,
            f0_b=0.04
        )
        
        # Rotate model slightly
        model_rotation = (frame_number * 0.5) % 360
        
        model_transform = rendering_service_pb2.ModelTransform(
            position_x=0,
            position_y=0,
            position_z=0,
            rotation_angle=model_rotation,
            rotation_axis_x=0,
            rotation_axis_y=1,
            rotation_axis_z=0,
            scale_x=0.1,
            scale_y=0.1,
            scale_z=0.1
        )
        
        return rendering_service_pb2.RenderRequest(
            request_id=frame_number,
            timestamp=int(time.time() * 1000),
            frame_number=frame_number,
            width=self.config.frame_width,
            height=self.config.frame_height,
            camera=camera,
            lighting=lighting,
            material=material,
            model_transform=model_transform,
            is_streaming=True,
            delta_time=1.0 / self.config.requests_per_second
        )
    
    def _calculate_current_rate(self, elapsed: float) -> float:
        """Calculate current request rate based on ramp-up/down."""
        target_rate = self.config.requests_per_second
        
        # Ramp-up phase
        if elapsed < self.config.ramp_up_seconds:
            return target_rate * (elapsed / self.config.ramp_up_seconds)
        
        # Ramp-down phase
        remaining = self.config.duration_seconds - elapsed
        if remaining < self.config.ramp_down_seconds:
            return target_rate * (remaining / self.config.ramp_down_seconds)
        
        return target_rate
    
    def _send_request(self, frame_number: int):
        """Send a single request and record metrics."""
        request = self._generate_request(frame_number)
        
        try:
            start_time = time.time()
            response = self.client.render_frame(request)
            latency = (time.time() - start_time) * 1000
            
            with self._lock:
                self.request_count += 1
                self.successful_count += 1
                self.latencies.append(latency)
                
                self.request_log.append({
                    'timestamp': time.time(),
                    'elapsed': time.time() - self.start_time,
                    'frame_number': frame_number,
                    'latency_ms': latency,
                    'success': True,
                    'replica_id': response.replica_id,
                    'geometry_time_ms': response.geometry_time_ms,
                    'lighting_time_ms': response.lighting_time_ms,
                    'postprocess_time_ms': response.postprocess_time_ms
                })
                
        except Exception as e:
            with self._lock:
                self.request_count += 1
                self.failed_count += 1
                
                self.request_log.append({
                    'timestamp': time.time(),
                    'elapsed': time.time() - self.start_time,
                    'frame_number': frame_number,
                    'latency_ms': 0,
                    'success': False,
                    'error': str(e)
                })
            
            logger.warning(f"Request {frame_number} failed: {e}")
    
    def run(self) -> LoadTestResult:
        """Run the load test."""
        self.start_time = time.time()
        self.log_event('TEST_START', f'Starting load test for {self.config.duration_seconds}s')
        
        frame_number = 0
        fault_injected = False
        
        # Set up signal handler
        def signal_handler(signum, frame):
            self.log_event('TEST_INTERRUPTED', 'Received interrupt signal')
            self._shutdown.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            while not self._shutdown.is_set():
                elapsed = time.time() - self.start_time
                
                if elapsed >= self.config.duration_seconds:
                    break
                
                # Inject fault at configured time
                if (self.config.inject_faults and 
                    not fault_injected and 
                    elapsed >= self.config.fault_injection_time):
                    
                    if self.fault_callback:
                        self.log_event('FAULT_INJECTION', 'Injecting fault')
                        self.fault_callback()
                        fault_injected = True
                
                # Calculate current rate and delay
                current_rate = self._calculate_current_rate(elapsed)
                if current_rate > 0:
                    delay = 1.0 / current_rate
                else:
                    delay = 0.1
                
                # Send request in separate thread to avoid blocking
                request_thread = threading.Thread(
                    target=self._send_request,
                    args=(frame_number,)
                )
                request_thread.start()
                
                frame_number += 1
                
                # Wait for next request
                time.sleep(delay)
                
                # Log progress every 10 seconds
                if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                    with self._lock:
                        success_rate = (
                            self.successful_count / self.request_count * 100
                            if self.request_count > 0 else 0
                        )
                    logger.info(
                        f"Progress: {elapsed:.0f}s / {self.config.duration_seconds}s, "
                        f"Requests: {self.request_count}, Success: {success_rate:.1f}%"
                    )
        
        finally:
            self.end_time = time.time()
            self.log_event('TEST_END', f'Test completed after {self.end_time - self.start_time:.1f}s')
        
        return self._calculate_results()
    
    def _calculate_results(self) -> LoadTestResult:
        """Calculate final test results."""
        with self._lock:
            if not self.latencies:
                return LoadTestResult(
                    start_time=self.start_time,
                    end_time=self.end_time,
                    total_requests=self.request_count,
                    successful_requests=self.successful_count,
                    failed_requests=self.failed_count,
                    avg_latency_ms=0,
                    p50_latency_ms=0,
                    p95_latency_ms=0,
                    p99_latency_ms=0,
                    min_latency_ms=0,
                    max_latency_ms=0,
                    throughput_rps=0,
                    request_log=list(self.request_log),
                    events=self.events
                )
            
            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)
            
            duration = self.end_time - self.start_time
            
            return LoadTestResult(
                start_time=self.start_time,
                end_time=self.end_time,
                total_requests=self.request_count,
                successful_requests=self.successful_count,
                failed_requests=self.failed_count,
                avg_latency_ms=sum(self.latencies) / n,
                p50_latency_ms=sorted_latencies[int(n * 0.50)],
                p95_latency_ms=sorted_latencies[int(n * 0.95)],
                p99_latency_ms=sorted_latencies[int(n * 0.99)],
                min_latency_ms=min(self.latencies),
                max_latency_ms=max(self.latencies),
                throughput_rps=self.successful_count / duration if duration > 0 else 0,
                request_log=list(self.request_log),
                events=self.events
            )
    
    def stop(self):
        """Stop the load test."""
        self._shutdown.set()


def save_results(result: LoadTestResult, config: LoadGeneratorConfig):
    """Save test results to JSON and CSV files."""
    # Save JSON
    json_data = {
        'config': {
            'duration_seconds': config.duration_seconds,
            'requests_per_second': config.requests_per_second,
            'frame_width': config.frame_width,
            'frame_height': config.frame_height,
            'inject_faults': config.inject_faults,
            'fault_injection_time': config.fault_injection_time
        },
        'summary': {
            'start_time': result.start_time,
            'end_time': result.end_time,
            'duration_seconds': result.end_time - result.start_time,
            'total_requests': result.total_requests,
            'successful_requests': result.successful_requests,
            'failed_requests': result.failed_requests,
            'success_rate': result.successful_requests / result.total_requests if result.total_requests > 0 else 0,
            'avg_latency_ms': result.avg_latency_ms,
            'p50_latency_ms': result.p50_latency_ms,
            'p95_latency_ms': result.p95_latency_ms,
            'p99_latency_ms': result.p99_latency_ms,
            'min_latency_ms': result.min_latency_ms,
            'max_latency_ms': result.max_latency_ms,
            'throughput_rps': result.throughput_rps
        },
        'events': result.events,
        'request_log': result.request_log
    }
    
    with open(config.output_file, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    logger.info(f"Results saved to {config.output_file}")
    
    # Save CSV for easy plotting
    with open(config.csv_output_file, 'w') as f:
        f.write("timestamp,elapsed,frame_number,latency_ms,success,replica_id\n")
        for entry in result.request_log:
            replica = entry.get('replica_id', '')
            f.write(
                f"{entry['timestamp']},{entry['elapsed']:.3f},{entry['frame_number']},"
                f"{entry['latency_ms']:.2f},{entry['success']},{replica}\n"
            )
    
    logger.info(f"CSV metrics saved to {config.csv_output_file}")


def print_summary(result: LoadTestResult):
    """Print a summary of the test results."""
    duration = result.end_time - result.start_time
    success_rate = (
        result.successful_requests / result.total_requests * 100
        if result.total_requests > 0 else 0
    )
    
    print("\n" + "=" * 60)
    print("LOAD TEST SUMMARY")
    print("=" * 60)
    print(f"Duration:           {duration:.1f} seconds")
    print(f"Total Requests:     {result.total_requests}")
    print(f"Successful:         {result.successful_requests}")
    print(f"Failed:             {result.failed_requests}")
    print(f"Success Rate:       {success_rate:.1f}%")
    print(f"Throughput:         {result.throughput_rps:.2f} req/sec")
    print("-" * 60)
    print("LATENCY METRICS")
    print("-" * 60)
    print(f"Average:            {result.avg_latency_ms:.2f} ms")
    print(f"P50 (Median):       {result.p50_latency_ms:.2f} ms")
    print(f"P95:                {result.p95_latency_ms:.2f} ms")
    print(f"P99:                {result.p99_latency_ms:.2f} ms")
    print(f"Min:                {result.min_latency_ms:.2f} ms")
    print(f"Max:                {result.max_latency_ms:.2f} ms")
    print("-" * 60)
    print("EVENTS")
    print("-" * 60)
    for event in result.events:
        print(f"[{event['elapsed']:.1f}s] {event['event_type']}: {event['message']}")
    print("=" * 60)


def main():
    """Main entry point for the load generator."""
    parser = argparse.ArgumentParser(description='Rendering Service Load Generator')
    parser.add_argument('--duration', type=float, default=60.0,
                       help='Test duration in seconds')
    parser.add_argument('--rate', type=float, default=10.0,
                       help='Requests per second')
    parser.add_argument('--width', type=int, default=320,
                       help='Frame width')
    parser.add_argument('--height', type=int, default=240,
                       help='Frame height')
    parser.add_argument('--inject-faults', action='store_true',
                       help='Inject faults during test')
    parser.add_argument('--fault-time', type=float, default=30.0,
                       help='Time to inject fault (seconds)')
    parser.add_argument('--output', type=str, default='load_test_results.json',
                       help='Output JSON file')
    parser.add_argument('--csv', type=str, default='performance_metrics.csv',
                       help='Output CSV file')
    parser.add_argument('--base-port', type=int, default=50051,
                       help='Base port for replicas')
    parser.add_argument('--num-replicas', type=int, default=2,
                       help='Number of replicas')
    
    args = parser.parse_args()
    
    config = LoadGeneratorConfig(
        duration_seconds=args.duration,
        requests_per_second=args.rate,
        frame_width=args.width,
        frame_height=args.height,
        inject_faults=args.inject_faults,
        fault_injection_time=args.fault_time,
        output_file=args.output,
        csv_output_file=args.csv
    )
    
    # Create client
    client = create_client(base_port=args.base_port, num_replicas=args.num_replicas)
    
    # Optional fault injection callback
    fault_callback = None
    if args.inject_faults:
        # This would need access to the replica manager
        # For standalone client mode, we can't inject faults
        logger.warning("Fault injection requires running with integrated mode")
    
    # Create and run load generator
    generator = LoadGenerator(client, config, fault_callback)
    
    try:
        result = generator.run()
        print_summary(result)
        save_results(result, config)
    finally:
        client.close()


if __name__ == '__main__':
    main()
