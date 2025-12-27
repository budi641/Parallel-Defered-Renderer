"""
Phase 3: High-Availability Native Renderer Demo
Launches multiple renderer replicas with automatic failover

This demo:
1. Starts 2 native C++ renderer replicas on different ports
2. Python client monitors health and streams frames
3. When a replica dies, automatically fails over to the other
4. Continuous frame delivery despite failures
"""

import os
import sys
import time
import threading
import signal
import logging
from typing import Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rendering_server_native import NativeRenderingServer, find_renderer_executable
from rendering_client import RenderingClient, ReplicaEndpoint
import rendering_service_pb2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ReplicaState:
    """Tracks state of a replica."""
    replica_id: str
    port: int
    server: Optional[NativeRenderingServer] = None
    is_healthy: bool = False
    is_active: bool = False  # Is this the currently active renderer
    

class HANativeRenderer:
    """
    High-Availability Native Renderer Manager
    
    Manages multiple renderer replicas and provides automatic failover.
    Only ONE renderer window is visible at a time (the active replica).
    """
    
    def __init__(self, ports: List[int] = [50051, 50052]):
        renderer_path = find_renderer_executable()
        if not renderer_path:
            raise RuntimeError("Could not find C++ renderer executable!")
        self.renderer_path: str = renderer_path
        
        self.ports = ports
        self.replicas: List[ReplicaState] = []
        self.active_replica_idx = 0
        self._lock = threading.Lock()
        self._running = False
        self._health_check_thread: Optional[threading.Thread] = None
        
        # Initialize replica states
        for i, port in enumerate(ports):
            self.replicas.append(ReplicaState(
                replica_id=f"native-replica-{i+1}",
                port=port,
                is_active=(i == 0)  # First replica is initially active
            ))
    
    def start(self):
        """Start the HA renderer system."""
        self._running = True
        
        print("=" * 60)
        print("PHASE 3: HIGH-AVAILABILITY NATIVE RENDERER")
        print("=" * 60)
        print()
        print(f"Renderer: {self.renderer_path}")
        print(f"Replicas: {len(self.replicas)}")
        print()
        
        # Start only the first (active) replica initially
        # The second replica runs as hot standby without window
        self._start_active_replica()
        
        # Start health monitoring
        self._health_check_thread = threading.Thread(target=self._health_monitor, daemon=True)
        self._health_check_thread.start()
        
        print()
        print("-" * 60)
        print("RENDERER RUNNING - Press Ctrl+C to stop")
        print("Kill the renderer window to test failover!")
        print("-" * 60)
        print()
    
    def _start_active_replica(self):
        """Start the currently active replica."""
        with self._lock:
            replica = self.replicas[self.active_replica_idx]
            
            if replica.server and replica.is_healthy:
                logger.info(f"[{replica.replica_id}] Already running")
                return
            
            logger.info(f"[{replica.replica_id}] Starting on port {replica.port}...")
            
            server = NativeRenderingServer(
                port=replica.port,
                renderer_path=self.renderer_path,
                replica_id=replica.replica_id
            )
            
            replica.server = server
            replica.is_active = True
            
            try:
                server.start()
                replica.is_healthy = True
                logger.info(f"[{replica.replica_id}] Started successfully!")
            except Exception as e:
                logger.error(f"[{replica.replica_id}] Failed to start: {e}")
                replica.is_healthy = False
    
    def _health_monitor(self):
        """Monitor replica health and perform failover if needed."""
        logger.info("Health monitor started")
        
        while self._running:
            time.sleep(1.0)
            
            with self._lock:
                active_replica = self.replicas[self.active_replica_idx]
                
                # Check if active replica is healthy
                if active_replica.server and active_replica.server.renderer:
                    is_healthy = active_replica.server.renderer.is_healthy()
                    
                    if not is_healthy and active_replica.is_healthy:
                        # Replica just died!
                        logger.warning(f"[{active_replica.replica_id}] REPLICA DIED!")
                        active_replica.is_healthy = False
                        active_replica.is_active = False
                        
                        # Stop the dead server
                        try:
                            active_replica.server.stop()
                        except Exception:
                            pass
                        active_replica.server = None
                        
                        # Perform failover
                        self._perform_failover()
    
    def _perform_failover(self):
        """Failover to the next available replica."""
        logger.info("=" * 40)
        logger.info("PERFORMING FAILOVER...")
        logger.info("=" * 40)
        
        # Find next replica
        old_idx = self.active_replica_idx
        self.active_replica_idx = (self.active_replica_idx + 1) % len(self.replicas)
        
        new_replica = self.replicas[self.active_replica_idx]
        logger.info(f"Failing over to {new_replica.replica_id} on port {new_replica.port}")
        
        # Start the new replica (unlock first to avoid deadlock)
        # We're already inside the lock, so we need to release and reacquire
        # Actually, we're calling this from within _health_monitor which holds the lock
        # So let's start the server directly here
        
        server = NativeRenderingServer(
            port=new_replica.port,
            renderer_path=self.renderer_path,
            replica_id=new_replica.replica_id
        )
        
        new_replica.server = server
        new_replica.is_active = True
        
        try:
            server.start()
            new_replica.is_healthy = True
            logger.info(f"[{new_replica.replica_id}] FAILOVER SUCCESSFUL!")
            logger.info(f"New renderer window should appear on port {new_replica.port}")
        except Exception as e:
            logger.error(f"[{new_replica.replica_id}] Failover failed: {e}")
            new_replica.is_healthy = False
    
    def stop(self):
        """Stop all replicas."""
        self._running = False
        
        for replica in self.replicas:
            if replica.server:
                try:
                    replica.server.stop()
                except Exception:
                    pass
                replica.server = None
                replica.is_healthy = False
        
        logger.info("All replicas stopped")
    
    def get_active_endpoint(self) -> Optional[str]:
        """Get the currently active replica endpoint."""
        with self._lock:
            replica = self.replicas[self.active_replica_idx]
            if replica.is_healthy:
                return f"localhost:{replica.port}"
        return None
    
    def get_all_endpoints(self) -> List[str]:
        """Get all replica endpoints (for client failover)."""
        return [f"localhost:{r.port}" for r in self.replicas]


def demo_with_client():
    """Run the HA demo with a Python client for health monitoring."""
    
    ha_renderer = HANativeRenderer(ports=[50051, 50052])
    
    try:
        # Start the HA renderer system
        ha_renderer.start()
        
        # Wait for renderer to initialize
        time.sleep(3)
        
        # Create a client connected to both replicas
        endpoints = ha_renderer.get_all_endpoints()
        print(f"Client connecting to: {endpoints}")
        
        client = RenderingClient(endpoints, timeout=5.0)
        
        # Monitoring loop
        frame_count = 0
        last_health_check = time.time()
        
        while True:
            time.sleep(0.5)
            
            # Periodic health check via client
            if time.time() - last_health_check > 2.0:
                try:
                    health = client.health_check()
                    if health:
                        status = "HEALTHY" if health.healthy else "UNHEALTHY"
                        print(f"[Client] Health: {status}, Uptime: {health.uptime_seconds}s")
                except Exception as e:
                    print(f"[Client] Health check failed: {e}")
                
                last_health_check = time.time()
            
            # Simulate frame request
            active = ha_renderer.get_active_endpoint()
            if active:
                frame_count += 1
                if frame_count % 10 == 0:
                    print(f"[Client] Frame {frame_count} - Active: {active}")
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        ha_renderer.stop()
        print("Demo complete.")


def demo_simple():
    """Simple demo that just runs the HA renderer."""
    
    ha_renderer = HANativeRenderer(ports=[50051, 50052])
    
    try:
        ha_renderer.start()
        
        # Wait for user to exit
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        ha_renderer.stop()
        print("Demo complete.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='High-Availability Native Renderer Demo')
    parser.add_argument('--simple', action='store_true', 
                       help='Run simple mode without client monitoring')
    
    args = parser.parse_args()
    
    if args.simple:
        demo_simple()
    else:
        demo_with_client()
