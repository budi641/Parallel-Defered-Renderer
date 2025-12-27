"""
Phase 3: High Availability Rendering Service
gRPC Server Implementation for Parallel Deferred Renderer

This module implements a gRPC service that wraps the rendering engine,
providing fault-tolerant distributed rendering with automatic failover.
"""

import grpc
from concurrent import futures
import time
import threading
import subprocess
import os
import sys
import signal
import logging
import uuid
import numpy as np
from collections import deque
from typing import Optional, Iterator
import json
from datetime import datetime

# Add the generated protobuf path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rendering_service_pb2
import rendering_service_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RenderingMetrics:
    """Collects and stores rendering performance metrics."""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.frame_times: deque = deque(maxlen=max_history)
        self.frame_history: deque = deque(maxlen=max_history)
        self.total_frames = 0
        self.failed_frames = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def record_frame(self, frame_number: int, latency_ms: float, success: bool):
        """Record metrics for a rendered frame."""
        with self._lock:
            timestamp = int(time.time() * 1000)
            self.frame_times.append(latency_ms)
            self.frame_history.append({
                'timestamp': timestamp,
                'frame_number': frame_number,
                'latency_ms': latency_ms,
                'success': success
            })
            self.total_frames += 1
            if not success:
                self.failed_frames += 1
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        with self._lock:
            if not self.frame_times:
                return {
                    'total_frames': 0,
                    'avg_time': 0,
                    'min_time': 0,
                    'max_time': 0,
                    'p95': 0,
                    'p99': 0,
                    'throughput': 0,
                    'uptime': time.time() - self.start_time
                }
            
            times = list(self.frame_times)
            sorted_times = sorted(times)
            n = len(sorted_times)
            
            uptime = time.time() - self.start_time
            throughput = self.total_frames / uptime if uptime > 0 else 0
            
            return {
                'total_frames': self.total_frames,
                'avg_time': sum(times) / n,
                'min_time': min(times),
                'max_time': max(times),
                'p95': sorted_times[int(n * 0.95)] if n > 0 else 0,
                'p99': sorted_times[int(n * 0.99)] if n > 0 else 0,
                'throughput': throughput,
                'uptime': uptime
            }
    
    def get_history(self) -> list:
        """Get frame history."""
        with self._lock:
            return list(self.frame_history)


class SimulatedRenderer:
    """
    Simulates the deferred rendering pipeline.
    In production, this would call the actual C++ renderer via subprocess or FFI.
    """
    
    def __init__(self, replica_id: str, simulate_delay: bool = True):
        self.replica_id = replica_id
        self.simulate_delay = simulate_delay
        self.frame_count = 0
        logger.info(f"[{replica_id}] SimulatedRenderer initialized")
    
    def render_frame(self, request: rendering_service_pb2.RenderRequest) -> dict:
        """
        Simulate rendering a frame.
        Returns dict with frame data and timing information.
        """
        start_time = time.time()
        
        # Simulate geometry pass
        geometry_start = time.time()
        if self.simulate_delay:
            time.sleep(np.random.uniform(0.005, 0.015))  # 5-15ms
        geometry_time = (time.time() - geometry_start) * 1000
        
        # Simulate lighting pass
        lighting_start = time.time()
        if self.simulate_delay:
            time.sleep(np.random.uniform(0.008, 0.020))  # 8-20ms
        lighting_time = (time.time() - lighting_start) * 1000
        
        # Simulate post-processing pass
        postprocess_start = time.time()
        if self.simulate_delay:
            time.sleep(np.random.uniform(0.003, 0.010))  # 3-10ms
        postprocess_time = (time.time() - postprocess_start) * 1000
        
        # Generate simulated frame data (gradient pattern based on camera position)
        width = request.width if request.width > 0 else 320
        height = request.height if request.height > 0 else 240
        
        # Create a simple gradient pattern that changes with camera position
        cam_x = request.camera.position_x if request.HasField('camera') else 0
        cam_y = request.camera.position_y if request.HasField('camera') else 0
        
        # Generate frame as numpy array then convert to bytes
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                frame[y, x, 0] = int((x / width * 255 + cam_x * 10) % 256)  # R
                frame[y, x, 1] = int((y / height * 255 + cam_y * 10) % 256)  # G
                frame[y, x, 2] = int((self.frame_count % 256))  # B
        
        self.frame_count += 1
        total_time = (time.time() - start_time) * 1000
        
        return {
            'frame_data': frame.tobytes(),
            'width': width,
            'height': height,
            'geometry_time': geometry_time,
            'lighting_time': lighting_time,
            'postprocess_time': postprocess_time,
            'total_time': total_time
        }


class RenderingServiceServicer(rendering_service_pb2_grpc.RenderingServiceServicer):
    """
    gRPC service implementation for the rendering service.
    Handles rendering requests and provides health check functionality.
    """
    
    def __init__(self, replica_id: str, port: int):
        self.replica_id = replica_id
        self.port = port
        self.start_time = time.time()
        self.renderer = SimulatedRenderer(replica_id)
        self.metrics = RenderingMetrics()
        self.is_healthy = True
        self._shutdown = False
        
        logger.info(f"[{replica_id}] RenderingServiceServicer initialized on port {port}")
    
    def RenderFrame(self, request: rendering_service_pb2.RenderRequest, 
                    context: grpc.ServicerContext) -> rendering_service_pb2.RenderResponse:
        """Handle a single frame render request."""
        if not self.is_healthy:
            context.abort(grpc.StatusCode.UNAVAILABLE, "Service is unhealthy")
        
        timestamp_received = int(time.time() * 1000)
        
        try:
            # Render the frame
            result = self.renderer.render_frame(request)
            timestamp_completed = int(time.time() * 1000)
            
            # Record metrics
            latency = result['total_time']
            self.metrics.record_frame(request.frame_number, latency, True)
            
            # Log the request
            logger.info(f"[{self.replica_id}] Rendered frame {request.frame_number} "
                       f"in {latency:.2f}ms")
            
            return rendering_service_pb2.RenderResponse(
                request_id=request.request_id,
                timestamp_received=timestamp_received,
                timestamp_completed=timestamp_completed,
                frame_number=request.frame_number,
                frame_data=result['frame_data'],
                width=result['width'],
                height=result['height'],
                encoding='raw',
                geometry_time_ms=result['geometry_time'],
                lighting_time_ms=result['lighting_time'],
                postprocess_time_ms=result['postprocess_time'],
                total_time_ms=result['total_time'],
                success=True,
                error_message='',
                replica_id=self.replica_id
            )
            
        except Exception as e:
            logger.error(f"[{self.replica_id}] Error rendering frame: {e}")
            self.metrics.record_frame(request.frame_number, 0, False)
            return rendering_service_pb2.RenderResponse(
                request_id=request.request_id,
                timestamp_received=timestamp_received,
                timestamp_completed=int(time.time() * 1000),
                frame_number=request.frame_number,
                success=False,
                error_message=str(e),
                replica_id=self.replica_id
            )
    
    def StreamFrames(self, request_iterator: Iterator[rendering_service_pb2.RenderRequest],
                     context: grpc.ServicerContext) -> Iterator[rendering_service_pb2.RenderResponse]:
        """Handle streaming frame render requests."""
        logger.info(f"[{self.replica_id}] Starting streaming session")
        
        for request in request_iterator:
            if self._shutdown or not self.is_healthy:
                break
            
            response = self.RenderFrame(request, context)
            yield response
        
        logger.info(f"[{self.replica_id}] Streaming session ended")
    
    def HealthCheck(self, request: rendering_service_pb2.HealthCheckRequest,
                    context: grpc.ServicerContext) -> rendering_service_pb2.HealthCheckResponse:
        """Health check endpoint for replica management."""
        stats = self.metrics.get_stats()
        
        return rendering_service_pb2.HealthCheckResponse(
            healthy=self.is_healthy,
            replica_id=self.replica_id,
            uptime_seconds=int(stats['uptime']),
            frames_rendered=stats['total_frames'],
            avg_latency_ms=stats['avg_time'],
            load_percentage=min(100.0, stats['throughput'] * 2)  # Rough estimate
        )
    
    def GetStats(self, request: rendering_service_pb2.StatsRequest,
                 context: grpc.ServicerContext) -> rendering_service_pb2.StatsResponse:
        """Get detailed statistics."""
        stats = self.metrics.get_stats()
        
        response = rendering_service_pb2.StatsResponse(
            replica_id=self.replica_id,
            total_frames_rendered=stats['total_frames'],
            avg_frame_time_ms=stats['avg_time'],
            min_frame_time_ms=stats['min_time'],
            max_frame_time_ms=stats['max_time'],
            p95_latency_ms=stats['p95'],
            p99_latency_ms=stats['p99'],
            throughput_fps=stats['throughput'],
            uptime_seconds=int(stats['uptime'])
        )
        
        if request.include_history:
            for entry in self.metrics.get_history():
                response.frame_history.append(
                    rendering_service_pb2.FrameMetric(
                        timestamp=entry['timestamp'],
                        frame_number=entry['frame_number'],
                        latency_ms=entry['latency_ms'],
                        success=entry['success']
                    )
                )
        
        return response
    
    def set_unhealthy(self):
        """Mark the service as unhealthy (for fault injection)."""
        self.is_healthy = False
        logger.warning(f"[{self.replica_id}] Service marked as UNHEALTHY")
    
    def shutdown(self):
        """Graceful shutdown."""
        self._shutdown = True
        logger.info(f"[{self.replica_id}] Shutdown initiated")


class RenderingServer:
    """
    gRPC server wrapper that manages the rendering service.
    Supports graceful shutdown and health monitoring.
    """
    
    def __init__(self, port: int, replica_id: Optional[str] = None, max_workers: int = 10):
        self.port = port
        self.replica_id = replica_id or f"replica-{port}-{uuid.uuid4().hex[:8]}"
        self.max_workers = max_workers
        self.server: Optional[grpc.Server] = None
        self.servicer: Optional[RenderingServiceServicer] = None
        self._shutdown_event = threading.Event()
    
    def start(self):
        """Start the gRPC server."""
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_workers))
        self.servicer = RenderingServiceServicer(self.replica_id, self.port)
        
        rendering_service_pb2_grpc.add_RenderingServiceServicer_to_server(
            self.servicer, self.server
        )
        
        self.server.add_insecure_port(f'[::]:{self.port}')
        self.server.start()
        
        logger.info(f"[{self.replica_id}] Server started on port {self.port}")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"[{self.replica_id}] Received signal {signum}, initiating shutdown...")
        self.stop()
    
    def stop(self):
        """Stop the gRPC server gracefully."""
        if self.servicer:
            self.servicer.shutdown()
        if self.server:
            self.server.stop(grace=5)
        self._shutdown_event.set()
        logger.info(f"[{self.replica_id}] Server stopped")
    
    def wait_for_termination(self):
        """Block until server is terminated."""
        self._shutdown_event.wait()
    
    def serve_forever(self):
        """Start and block until termination."""
        self.start()
        try:
            if self.server:
                self.server.wait_for_termination()
        except KeyboardInterrupt:
            self.stop()


def run_server(port: int, replica_id: Optional[str] = None):
    """Convenience function to run a rendering server."""
    server = RenderingServer(port, replica_id)
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Rendering gRPC Server')
    parser.add_argument('--port', type=int, default=50051, help='Port to listen on')
    parser.add_argument('--replica-id', type=str, default=None, help='Replica identifier')
    
    args = parser.parse_args()
    
    run_server(args.port, args.replica_id)
