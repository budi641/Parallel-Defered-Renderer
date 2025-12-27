"""
Phase 3: High Availability Rendering Service
Replica Manager - Handles automatic failover between rendering replicas

This module manages multiple rendering service replicas and provides
automatic failover when a replica becomes unavailable.
"""

import grpc
import time
import threading
import subprocess
import sys
import os
import logging
import signal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

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


class ReplicaState(Enum):
    """Possible states of a replica."""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ReplicaInfo:
    """Information about a single replica."""
    replica_id: str
    port: int
    state: ReplicaState = ReplicaState.STARTING
    process: Optional[subprocess.Popen] = None
    channel: Optional[grpc.Channel] = None
    stub: Optional[rendering_service_pb2_grpc.RenderingServiceStub] = None
    last_health_check: float = 0
    consecutive_failures: int = 0
    total_requests_served: int = 0
    start_time: float = field(default_factory=time.time)
    
    def __post_init__(self):
        if self.channel is None:
            self._connect()
    
    def _connect(self):
        """Establish connection to the replica."""
        try:
            self.channel = grpc.insecure_channel(
                f'localhost:{self.port}',
                options=[
                    ('grpc.keepalive_time_ms', 10000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.http2.max_pings_without_data', 0),
                ]
            )
            self.stub = rendering_service_pb2_grpc.RenderingServiceStub(self.channel)
        except Exception as e:
            logger.error(f"[{self.replica_id}] Failed to connect: {e}")
            self.state = ReplicaState.FAILED
    
    def close(self):
        """Close the connection to the replica."""
        if self.channel:
            self.channel.close()
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class ReplicaManager:
    """
    Manages multiple rendering service replicas with automatic failover.
    
    Features:
    - Health monitoring with configurable intervals
    - Automatic failover to healthy replicas
    - Load balancing across healthy replicas
    - Automatic restart of failed replicas
    """
    
    def __init__(
        self,
        base_port: int = 50051,
        num_replicas: int = 2,
        health_check_interval: float = 2.0,
        max_consecutive_failures: int = 3,
        auto_restart: bool = True
    ):
        self.base_port = base_port
        self.num_replicas = num_replicas
        self.health_check_interval = health_check_interval
        self.max_consecutive_failures = max_consecutive_failures
        self.auto_restart = auto_restart
        
        self.replicas: Dict[str, ReplicaInfo] = {}
        self.active_replica_id: Optional[str] = None
        self._lock = threading.Lock()
        self._health_thread: Optional[threading.Thread] = None
        self._shutdown = threading.Event()
        
        # Event log for demo purposes
        self.event_log: List[dict] = []
    
    def log_event(self, event_type: str, replica_id: str, message: str):
        """Log an event for later analysis."""
        event = {
            'timestamp': datetime.now().isoformat(),
            'epoch': time.time(),
            'event_type': event_type,
            'replica_id': replica_id,
            'message': message
        }
        self.event_log.append(event)
        logger.info(f"[EVENT] {event_type}: {replica_id} - {message}")
    
    def start_replicas(self):
        """Start all rendering service replicas."""
        logger.info(f"Starting {self.num_replicas} replicas...")
        
        for i in range(self.num_replicas):
            port = self.base_port + i
            replica_id = f"replica-{i+1}"
            self._start_replica(replica_id, port)
        
        # Wait for replicas to start
        time.sleep(2)
        
        # Start health monitoring
        self._start_health_monitoring()
        
        # Set initial active replica
        self._select_active_replica()
    
    def _start_replica(self, replica_id: str, port: int):
        """Start a single replica process."""
        script_path = os.path.join(os.path.dirname(__file__), 'rendering_server.py')
        
        process = subprocess.Popen(
            [sys.executable, script_path, '--port', str(port), '--replica-id', replica_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        replica = ReplicaInfo(
            replica_id=replica_id,
            port=port,
            state=ReplicaState.STARTING,
            process=process
        )
        
        with self._lock:
            self.replicas[replica_id] = replica
        
        self.log_event('REPLICA_STARTED', replica_id, f'Started on port {port}')
        logger.info(f"Started {replica_id} on port {port} (PID: {process.pid})")
    
    def _start_health_monitoring(self):
        """Start the health monitoring thread."""
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()
        logger.info("Health monitoring started")
    
    def _health_check_loop(self):
        """Continuously check health of all replicas."""
        while not self._shutdown.is_set():
            try:
                self._check_all_replicas()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            self._shutdown.wait(self.health_check_interval)
    
    def _check_all_replicas(self):
        """Check health of all replicas and handle failures."""
        with self._lock:
            replica_ids = list(self.replicas.keys())
        
        for replica_id in replica_ids:
            self._check_replica_health(replica_id)
    
    def _check_replica_health(self, replica_id: str):
        """Check health of a single replica."""
        with self._lock:
            replica = self.replicas.get(replica_id)
            if not replica or replica.stub is None:
                return
        
        try:
            # Perform health check with timeout
            request = rendering_service_pb2.HealthCheckRequest(client_id="manager")
            response = replica.stub.HealthCheck(request, timeout=2.0)
            
            with self._lock:
                if response.healthy:
                    if replica.state != ReplicaState.HEALTHY:
                        self.log_event('REPLICA_HEALTHY', replica_id, 'Replica became healthy')
                    replica.state = ReplicaState.HEALTHY
                    replica.consecutive_failures = 0
                    replica.last_health_check = time.time()
                else:
                    self._handle_unhealthy_replica(replica_id, "Reported unhealthy")
                    
        except grpc.RpcError as e:
            self._handle_failed_health_check(replica_id, str(e))
        except Exception as e:
            self._handle_failed_health_check(replica_id, str(e))
    
    def _handle_failed_health_check(self, replica_id: str, error: str):
        """Handle a failed health check."""
        with self._lock:
            replica = self.replicas.get(replica_id)
            if not replica:
                return
            
            replica.consecutive_failures += 1
            
            if replica.consecutive_failures >= self.max_consecutive_failures:
                replica.state = ReplicaState.FAILED
                self.log_event('REPLICA_FAILED', replica_id, 
                             f'Failed after {replica.consecutive_failures} consecutive failures: {error}')
                
                # Trigger failover if this was the active replica
                if self.active_replica_id == replica_id:
                    self._trigger_failover(replica_id)
                
                # Auto-restart if enabled
                if self.auto_restart:
                    self._schedule_restart(replica_id)
            else:
                replica.state = ReplicaState.UNHEALTHY
                self.log_event('REPLICA_UNHEALTHY', replica_id, 
                             f'Health check failed ({replica.consecutive_failures}): {error}')
    
    def _handle_unhealthy_replica(self, replica_id: str, reason: str):
        """Handle an unhealthy replica."""
        with self._lock:
            replica = self.replicas.get(replica_id)
            if not replica:
                return
            
            replica.state = ReplicaState.UNHEALTHY
            replica.consecutive_failures += 1
            
        self.log_event('REPLICA_UNHEALTHY', replica_id, reason)
        
        if self.active_replica_id == replica_id:
            self._trigger_failover(replica_id)
    
    def _trigger_failover(self, failed_replica_id: str):
        """Trigger failover from a failed replica to a healthy one."""
        logger.warning(f"Triggering failover from {failed_replica_id}")
        self.log_event('FAILOVER_TRIGGERED', failed_replica_id, 'Searching for healthy replica')
        
        self._select_active_replica(exclude=[failed_replica_id])
    
    def _select_active_replica(self, exclude: Optional[List[str]] = None):
        """Select a healthy replica to be the active one."""
        exclude = exclude or []
        
        with self._lock:
            for replica_id, replica in self.replicas.items():
                if replica_id not in exclude and replica.state == ReplicaState.HEALTHY:
                    old_active = self.active_replica_id
                    self.active_replica_id = replica_id
                    self.log_event('ACTIVE_REPLICA_CHANGED', replica_id, 
                                 f'Active replica changed from {old_active}')
                    logger.info(f"Active replica is now: {replica_id}")
                    return
            
            # No healthy replica found, try starting replicas
            for replica_id, replica in self.replicas.items():
                if replica_id not in exclude and replica.state == ReplicaState.STARTING:
                    self.active_replica_id = replica_id
                    logger.warning(f"No healthy replica, using starting replica: {replica_id}")
                    return
        
        logger.error("No available replicas!")
        self.log_event('NO_REPLICAS_AVAILABLE', 'manager', 'All replicas unavailable')
    
    def _schedule_restart(self, replica_id: str):
        """Schedule a restart for a failed replica."""
        def do_restart():
            time.sleep(5)  # Wait before restarting
            with self._lock:
                replica = self.replicas.get(replica_id)
                if replica and replica.state == ReplicaState.FAILED:
                    port = replica.port
                    replica.close()
                    del self.replicas[replica_id]
            
            self._start_replica(replica_id, port)
            self.log_event('REPLICA_RESTARTED', replica_id, 'Replica restarted automatically')
        
        restart_thread = threading.Thread(target=do_restart, daemon=True)
        restart_thread.start()
    
    def get_active_stub(self) -> Optional[Tuple[str, rendering_service_pb2_grpc.RenderingServiceStub]]:
        """Get the stub for the currently active replica."""
        with self._lock:
            if self.active_replica_id and self.active_replica_id in self.replicas:
                replica = self.replicas[self.active_replica_id]
                if replica.stub is not None:
                    return (replica.replica_id, replica.stub)
        return None
    
    def get_any_healthy_stub(self) -> Optional[Tuple[str, rendering_service_pb2_grpc.RenderingServiceStub]]:
        """Get a stub for any healthy replica."""
        with self._lock:
            for replica_id, replica in self.replicas.items():
                if replica.state == ReplicaState.HEALTHY and replica.stub:
                    return (replica_id, replica.stub)
        return None
    
    def kill_replica(self, replica_id: str):
        """Kill a specific replica (for fault injection testing)."""
        with self._lock:
            replica = self.replicas.get(replica_id)
            if replica and replica.process:
                logger.warning(f"FAULT INJECTION: Killing {replica_id}")
                self.log_event('FAULT_INJECTION', replica_id, 'Replica killed for testing')
                
                if os.name == 'nt':
                    # Windows
                    replica.process.terminate()
                else:
                    # Unix
                    os.kill(replica.process.pid, signal.SIGKILL)
                
                replica.state = ReplicaState.FAILED
    
    def get_status(self) -> dict:
        """Get current status of all replicas."""
        with self._lock:
            return {
                'active_replica': self.active_replica_id,
                'replicas': {
                    rid: {
                        'state': r.state.value,
                        'port': r.port,
                        'consecutive_failures': r.consecutive_failures,
                        'total_requests': r.total_requests_served,
                        'uptime': time.time() - r.start_time
                    }
                    for rid, r in self.replicas.items()
                }
            }
    
    def get_event_log(self) -> List[dict]:
        """Get the event log."""
        return self.event_log.copy()
    
    def shutdown(self):
        """Shutdown all replicas and stop monitoring."""
        logger.info("Shutting down replica manager...")
        self._shutdown.set()
        
        with self._lock:
            for replica in self.replicas.values():
                replica.close()
            self.replicas.clear()
        
        self.log_event('MANAGER_SHUTDOWN', 'manager', 'Replica manager shut down')


class HighAvailabilityClient:
    """
    Client that automatically handles failover between replicas.
    Uses the replica manager to route requests to healthy replicas.
    """
    
    def __init__(self, manager: ReplicaManager, max_retries: int = 3, retry_delay: float = 0.5):
        self.manager = manager
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_log: List[dict] = []
    
    def render_frame(self, request: rendering_service_pb2.RenderRequest) -> rendering_service_pb2.RenderResponse:
        """
        Render a frame with automatic retry and failover.
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            result = self.manager.get_active_stub()
            
            if not result:
                # Try any healthy replica
                result = self.manager.get_any_healthy_stub()
            
            if not result:
                logger.warning(f"No available replica, attempt {attempt + 1}/{self.max_retries}")
                time.sleep(self.retry_delay * (attempt + 1))
                continue
            
            replica_id, stub = result
            
            try:
                start_time = time.time()
                response = stub.RenderFrame(request, timeout=10.0)
                latency = (time.time() - start_time) * 1000
                
                # Log successful request
                self.request_log.append({
                    'timestamp': time.time(),
                    'request_id': request.request_id,
                    'frame_number': request.frame_number,
                    'replica_id': replica_id,
                    'latency_ms': latency,
                    'success': True
                })
                
                return response
                
            except grpc.RpcError as e:
                last_error = e
                logger.warning(f"Request to {replica_id} failed: {e}, retrying...")
                
                # Log failed request
                self.request_log.append({
                    'timestamp': time.time(),
                    'request_id': request.request_id,
                    'frame_number': request.frame_number,
                    'replica_id': replica_id,
                    'latency_ms': 0,
                    'success': False,
                    'error': str(e)
                })
                
                # Wait and retry
                time.sleep(self.retry_delay * (attempt + 1))
        
        # All retries exhausted
        raise Exception(f"All retries exhausted: {last_error}")
    
    def get_request_log(self) -> List[dict]:
        """Get the request log."""
        return self.request_log.copy()


def main():
    """Demo of the replica manager."""
    manager = ReplicaManager(num_replicas=2)
    
    try:
        manager.start_replicas()
        
        # Wait for replicas to be healthy
        time.sleep(5)
        
        print("\n=== Replica Status ===")
        print(json.dumps(manager.get_status(), indent=2))
        
        # Keep running
        while True:
            time.sleep(10)
            print("\n=== Current Status ===")
            print(json.dumps(manager.get_status(), indent=2))
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        manager.shutdown()


if __name__ == '__main__':
    main()
