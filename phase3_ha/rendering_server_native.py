"""
Phase 3: High Availability Rendering Service
Native Rendering Server - Launches actual C++ OpenGL renderer

This server launches the actual Parallel-Deferred-Renderer executable
and provides gRPC interface for health checks and metrics while the
renderer displays its window.
"""

import grpc
import time
import threading
import subprocess
import sys
import os
import logging
import signal
import uuid
from concurrent import futures
from typing import Optional
from dataclasses import dataclass, field

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


@dataclass
class RenderingMetrics:
    """Tracks rendering performance metrics."""
    frames_rendered: int = 0
    total_render_time: float = 0.0
    min_render_time: float = float('inf')
    max_render_time: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def avg_render_time(self) -> float:
        if self.frames_rendered == 0:
            return 0.0
        return self.total_render_time / self.frames_rendered
    
    @property
    def uptime(self) -> float:
        return time.time() - self.start_time


class NativeRenderer:
    """
    Wrapper that launches and manages the actual C++ renderer process.
    """
    
    def __init__(self, renderer_path: str, replica_id: str):
        self.renderer_path = renderer_path
        self.replica_id = replica_id
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.is_running = False
        
    def start(self):
        """Start the native renderer process."""
        with self._lock:
            if self.process and self.process.poll() is None:
                logger.warning(f"[{self.replica_id}] Renderer already running")
                return
            
            # Find the renderer executable
            if not os.path.exists(self.renderer_path):
                logger.error(f"Renderer not found: {self.renderer_path}")
                return
            
            # Get the project root directory where resources (shaders, models, textures) are located
            # Path: build_Debug/Debug/Renderer.exe -> need to go up to project root
            renderer_dir = os.path.dirname(self.renderer_path)  # Debug/
            renderer_dir = os.path.dirname(renderer_dir)  # build_Debug/
            renderer_dir = os.path.dirname(renderer_dir)  # project root
            
            logger.info(f"[{self.replica_id}] Starting native renderer: {self.renderer_path}")
            logger.info(f"[{self.replica_id}] Working directory: {renderer_dir}")
            
            try:
                # Start the renderer process
                self.process = subprocess.Popen(
                    [self.renderer_path],
                    cwd=renderer_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
                self.is_running = True
                logger.info(f"[{self.replica_id}] Renderer started (PID: {self.process.pid})")
                
                # Start a thread to monitor the process
                monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
                monitor_thread.start()
                
            except Exception as e:
                logger.error(f"[{self.replica_id}] Failed to start renderer: {e}")
                self.is_running = False
    
    def _monitor_process(self):
        """Monitor the renderer process and log when it exits."""
        if self.process:
            return_code = self.process.wait()
            self.is_running = False
            logger.info(f"[{self.replica_id}] Renderer exited with code: {return_code}")
    
    def stop(self):
        """Stop the native renderer process."""
        with self._lock:
            if self.process and self.process.poll() is None:
                logger.info(f"[{self.replica_id}] Stopping renderer...")
                try:
                    if os.name == 'nt':
                        # Windows: send CTRL_BREAK_EVENT
                        self.process.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        self.process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"[{self.replica_id}] Force killing renderer")
                        self.process.kill()
                        
                except Exception as e:
                    logger.error(f"[{self.replica_id}] Error stopping renderer: {e}")
                    
            self.is_running = False
    
    def is_healthy(self) -> bool:
        """Check if the renderer process is running."""
        with self._lock:
            if self.process:
                return self.process.poll() is None
            return False


class NativeRenderingServiceServicer(rendering_service_pb2_grpc.RenderingServiceServicer):
    """
    gRPC servicer that wraps the native C++ renderer.
    
    Since the actual rendering happens in the C++ process with its own window,
    this servicer primarily provides:
    - Health check responses
    - Stats collection
    - Process management
    """
    
    def __init__(self, replica_id: str, port: int, renderer: NativeRenderer):
        self.replica_id = replica_id
        self.port = port
        self.renderer = renderer
        self.metrics = RenderingMetrics()
        self.is_healthy = True
        self._shutdown = False
        
        logger.info(f"[{self.replica_id}] Native rendering service initialized on port {port}")
    
    def RenderFrame(self, request, context):
        """
        For native rendering, we don't actually render here.
        The C++ renderer runs independently with its own display.
        This just acknowledges the request for metrics purposes.
        """
        start_time = time.time()
        
        if not self.is_healthy or self._shutdown:
            return rendering_service_pb2.RenderResponse(
                request_id=request.request_id,
                success=False,
                error_message="Service is shutting down or unhealthy",
                replica_id=self.replica_id
            )
        
        if not self.renderer.is_healthy():
            return rendering_service_pb2.RenderResponse(
                request_id=request.request_id,
                success=False,
                error_message="Native renderer is not running",
                replica_id=self.replica_id
            )
        
        # Record metrics (the actual rendering is done by C++ process)
        render_time = (time.time() - start_time) * 1000
        
        self.metrics.frames_rendered += 1
        self.metrics.total_render_time += render_time
        self.metrics.min_render_time = min(self.metrics.min_render_time, render_time)
        self.metrics.max_render_time = max(self.metrics.max_render_time, render_time)
        
        return rendering_service_pb2.RenderResponse(
            request_id=request.request_id,
            timestamp_received=int(start_time * 1000),
            timestamp_completed=int(time.time() * 1000),
            frame_number=request.frame_number,
            frame_data=b'',  # No frame data - rendered to display
            width=request.width,
            height=request.height,
            encoding="native_display",
            total_time_ms=render_time,
            success=True,
            replica_id=self.replica_id
        )
    
    def StreamFrames(self, request_iterator, context):
        """Stream handler for native renderer."""
        for request in request_iterator:
            yield self.RenderFrame(request, context)
    
    def HealthCheck(self, request, context):
        """Health check that verifies the native renderer is running."""
        renderer_healthy = self.renderer.is_healthy()
        
        return rendering_service_pb2.HealthCheckResponse(
            healthy=self.is_healthy and renderer_healthy and not self._shutdown,
            replica_id=self.replica_id,
            uptime_seconds=int(self.metrics.uptime),
            frames_rendered=self.metrics.frames_rendered,
            avg_latency_ms=self.metrics.avg_render_time,
            load_percentage=0.0
        )
    
    def GetStats(self, request, context):
        """Get rendering statistics."""
        return rendering_service_pb2.StatsResponse(
            replica_id=self.replica_id,
            total_frames_rendered=self.metrics.frames_rendered,
            avg_frame_time_ms=self.metrics.avg_render_time,
            min_frame_time_ms=self.metrics.min_render_time if self.metrics.min_render_time != float('inf') else 0.0,
            max_frame_time_ms=self.metrics.max_render_time,
            throughput_fps=self.metrics.frames_rendered / max(1.0, self.metrics.uptime),
            uptime_seconds=int(self.metrics.uptime)
        )
    
    def set_unhealthy(self):
        """Mark service as unhealthy."""
        self.is_healthy = False
        logger.warning(f"[{self.replica_id}] Service marked as UNHEALTHY")
    
    def shutdown(self):
        """Graceful shutdown."""
        self._shutdown = True
        self.renderer.stop()
        logger.info(f"[{self.replica_id}] Shutdown initiated")


class NativeRenderingServer:
    """
    gRPC server that manages a native C++ renderer process.
    """
    
    def __init__(self, port: int, renderer_path: str, replica_id: Optional[str] = None, max_workers: int = 10):
        self.port = port
        self.renderer_path = renderer_path
        self.replica_id = replica_id or f"native-replica-{port}-{uuid.uuid4().hex[:8]}"
        self.max_workers = max_workers
        self.server: Optional[grpc.Server] = None
        self.servicer: Optional[NativeRenderingServiceServicer] = None
        self.renderer: Optional[NativeRenderer] = None
        self._shutdown_event = threading.Event()
    
    def start(self):
        """Start the native renderer and gRPC server."""
        # Create and start the native renderer
        self.renderer = NativeRenderer(self.renderer_path, self.replica_id)
        self.renderer.start()
        
        # Give the renderer time to initialize
        time.sleep(2)
        
        # Create gRPC server
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_workers))
        self.servicer = NativeRenderingServiceServicer(self.replica_id, self.port, self.renderer)
        
        rendering_service_pb2_grpc.add_RenderingServiceServicer_to_server(
            self.servicer, self.server
        )
        
        self.server.add_insecure_port(f'[::]:{self.port}')
        self.server.start()
        
        logger.info(f"[{self.replica_id}] gRPC server started on port {self.port}")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"[{self.replica_id}] Received signal {signum}, initiating shutdown...")
        self.stop()
    
    def stop(self):
        """Stop the gRPC server and native renderer."""
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


def find_renderer_executable() -> Optional[str]:
    """Find the C++ renderer executable."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check common locations
    candidates = [
        os.path.join(base_dir, "build_Debug", "Debug", "Parallel-Deferred-Renderer.exe"),
        os.path.join(base_dir, "build", "Debug", "Parallel-Deferred-Renderer.exe"),
        os.path.join(base_dir, "build", "Parallel-Deferred-Renderer.exe"),
        os.path.join(base_dir, "build", "Release", "Parallel-Deferred-Renderer.exe"),
        os.path.join(base_dir, "build_Release", "Release", "Parallel-Deferred-Renderer.exe"),
        # Linux/Mac
        os.path.join(base_dir, "build", "Parallel-Deferred-Renderer"),
    ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    
    return None


def run_server(port: int, replica_id: Optional[str] = None, renderer_path: Optional[str] = None):
    """Convenience function to run a native rendering server."""
    if renderer_path is None:
        renderer_path = find_renderer_executable()
        if renderer_path is None:
            logger.error("Could not find renderer executable. Please build the C++ project first.")
            return
    
    server = NativeRenderingServer(port, renderer_path, replica_id)
    server.serve_forever()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Native Rendering gRPC Server')
    parser.add_argument('--port', type=int, default=50051, help='Port to listen on')
    parser.add_argument('--replica-id', type=str, default=None, help='Replica identifier')
    parser.add_argument('--renderer-path', type=str, default=None, help='Path to renderer executable')
    
    args = parser.parse_args()
    
    run_server(args.port, args.replica_id, args.renderer_path)
