"""
Phase 3: High Availability Rendering Service
Rendering Client with Auto-Retry and Failover Support

This module implements a client that connects to the rendering service
with automatic retry logic and failover to backup replicas.
"""

import grpc
import time
import threading
import logging
import sys
import os
from typing import Optional, List, Tuple, Iterator
from dataclasses import dataclass
from collections import deque
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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


@dataclass
class ReplicaEndpoint:
    """Represents a single replica endpoint."""
    host: str
    port: int
    priority: int = 0  # Lower is higher priority
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


class RenderingClient:
    """
    High-availability rendering client with automatic failover.
    
    Features:
    - Automatic retry with exponential backoff
    - Failover to backup replicas
    - Request/response logging with timestamps
    - Performance metrics collection
    """
    
    def __init__(
        self,
        replicas: List[ReplicaEndpoint] | List[str],
        timeout: float = 10.0,
        max_retries: int = 3,
        initial_retry_delay: float = 0.5,
        max_retry_delay: float = 5.0
    ):
        # Convert string addresses to ReplicaEndpoint objects
        converted_replicas: List[ReplicaEndpoint] = []
        for i, replica in enumerate(replicas):
            if isinstance(replica, str):
                # Parse "host:port" string
                if ':' in replica:
                    host, port = replica.rsplit(':', 1)
                    converted_replicas.append(ReplicaEndpoint(host=host, port=int(port), priority=i))
                else:
                    converted_replicas.append(ReplicaEndpoint(host=replica, port=50051, priority=i))
            else:
                converted_replicas.append(replica)
        
        self.replicas = sorted(converted_replicas, key=lambda r: r.priority)
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        
        self.channels: dict = {}
        self.stubs: dict = {}
        self.current_replica_idx = 0
        self._lock = threading.Lock()
        
        # Metrics
        self.request_log: deque = deque(maxlen=100000)
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency = 0.0
        self.retries_count = 0
        self.failovers_count = 0
        
        self._connect_all()
    
    def _connect_all(self):
        """Establish connections to all replicas."""
        for replica in self.replicas:
            self._connect(replica)
    
    def _connect(self, replica: ReplicaEndpoint):
        """Establish connection to a single replica."""
        try:
            channel = grpc.insecure_channel(
                replica.address,
                options=[
                    ('grpc.keepalive_time_ms', 10000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.enable_retries', 1),
                    ('grpc.service_config', json.dumps({
                        'methodConfig': [{
                            'name': [{'service': 'rendering.RenderingService'}],
                            'retryPolicy': {
                                'maxAttempts': 3,
                                'initialBackoff': '0.5s',
                                'maxBackoff': '5s',
                                'backoffMultiplier': 2,
                                'retryableStatusCodes': ['UNAVAILABLE', 'DEADLINE_EXCEEDED']
                            }
                        }]
                    }))
                ]
            )
            stub = rendering_service_pb2_grpc.RenderingServiceStub(channel)
            
            self.channels[replica.address] = channel
            self.stubs[replica.address] = stub
            
            logger.info(f"Connected to replica at {replica.address}")
        except Exception as e:
            logger.error(f"Failed to connect to {replica.address}: {e}")
    
    def _get_current_stub(self) -> Tuple[str, Optional[rendering_service_pb2_grpc.RenderingServiceStub]]:
        """Get the stub for the current primary replica."""
        with self._lock:
            replica = self.replicas[self.current_replica_idx]
            return replica.address, self.stubs.get(replica.address)
    
    def _failover(self):
        """Switch to the next available replica."""
        with self._lock:
            old_idx = self.current_replica_idx
            self.current_replica_idx = (self.current_replica_idx + 1) % len(self.replicas)
            self.failovers_count += 1
            
            old_addr = self.replicas[old_idx].address
            new_addr = self.replicas[self.current_replica_idx].address
            
            logger.warning(f"Failover: {old_addr} -> {new_addr}")
    
    def _log_request(
        self,
        request_id: int,
        frame_number: int,
        replica_address: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
        retry_count: int = 0
    ):
        """Log a request for later analysis."""
        entry = {
            'timestamp': time.time(),
            'request_id': request_id,
            'frame_number': frame_number,
            'replica': replica_address,
            'latency_ms': latency_ms,
            'success': success,
            'error': error,
            'retry_count': retry_count
        }
        self.request_log.append(entry)
        
        with self._lock:
            self.total_requests += 1
            if success:
                self.successful_requests += 1
                self.total_latency += latency_ms
            else:
                self.failed_requests += 1
            self.retries_count += retry_count
    
    def render_frame(self, request: rendering_service_pb2.RenderRequest) -> rendering_service_pb2.RenderResponse:
        """
        Render a frame with automatic retry and failover.
        
        Args:
            request: The render request
            
        Returns:
            RenderResponse from the service
            
        Raises:
            Exception if all retries and failovers are exhausted
        """
        last_error = None
        total_retries = 0
        
        for failover_attempt in range(len(self.replicas)):
            address, stub = self._get_current_stub()
            
            if not stub:
                self._failover()
                continue
            
            for retry_attempt in range(self.max_retries):
                try:
                    start_time = time.time()
                    response = stub.RenderFrame(request, timeout=self.timeout)
                    latency = (time.time() - start_time) * 1000
                    
                    self._log_request(
                        request.request_id,
                        request.frame_number,
                        address,
                        latency,
                        True,
                        retry_count=total_retries
                    )
                    
                    return response
                    
                except grpc.RpcError as e:
                    last_error = e
                    total_retries += 1
                    
                    status_code = e.code() if hasattr(e, 'code') else None
                    error_msg = str(e)
                    
                    logger.warning(
                        f"Request failed (attempt {retry_attempt + 1}/{self.max_retries}): "
                        f"{status_code} - {error_msg}"
                    )
                    
                    self._log_request(
                        request.request_id,
                        request.frame_number,
                        address,
                        0,
                        False,
                        error=error_msg,
                        retry_count=total_retries
                    )
                    
                    # Check if we should retry or failover
                    if status_code in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED]:
                        if retry_attempt < self.max_retries - 1:
                            delay = min(
                                self.initial_retry_delay * (2 ** retry_attempt),
                                self.max_retry_delay
                            )
                            time.sleep(delay)
                        else:
                            # Exhausted retries, try failover
                            break
                    else:
                        # Non-retryable error
                        break
                        
                except Exception as e:
                    last_error = e
                    logger.error(f"Unexpected error: {e}")
                    break
            
            # Failed on current replica, try failover
            if failover_attempt < len(self.replicas) - 1:
                self._failover()
        
        # All replicas exhausted
        raise Exception(f"All replicas and retries exhausted: {last_error}")
    
    def stream_frames(
        self,
        requests: Iterator[rendering_service_pb2.RenderRequest]
    ) -> Iterator[rendering_service_pb2.RenderResponse]:
        """
        Stream frames with automatic failover.
        
        Note: Streaming failover is more complex. This implementation
        will fail-fast and let the caller retry.
        """
        address, stub = self._get_current_stub()
        
        if not stub:
            raise Exception("No available replica")
        
        try:
            for response in stub.StreamFrames(requests, timeout=None):
                yield response
        except grpc.RpcError as e:
            logger.error(f"Stream error: {e}")
            self._failover()
            raise
    
    def health_check(self, replica_address: Optional[str] = None) -> Optional[rendering_service_pb2.HealthCheckResponse]:
        """Perform health check on a replica."""
        if replica_address:
            stub = self.stubs.get(replica_address)
        else:
            _, stub = self._get_current_stub()
        
        if not stub:
            return None
        
        try:
            request = rendering_service_pb2.HealthCheckRequest(client_id="client")
            return stub.HealthCheck(request, timeout=2.0)
        except grpc.RpcError as e:
            logger.warning(f"Health check failed: {e}")
            return None
    
    def get_stats(self, replica_address: Optional[str] = None) -> Optional[rendering_service_pb2.StatsResponse]:
        """Get stats from a replica."""
        if replica_address:
            stub = self.stubs.get(replica_address)
        else:
            _, stub = self._get_current_stub()
        
        if not stub:
            return None
        
        try:
            request = rendering_service_pb2.StatsRequest(
                client_id="client",
                include_history=True
            )
            return stub.GetStats(request, timeout=5.0)
        except grpc.RpcError as e:
            logger.warning(f"Get stats failed: {e}")
            return None
    
    def get_metrics(self) -> dict:
        """Get client-side metrics."""
        with self._lock:
            avg_latency = (
                self.total_latency / self.successful_requests
                if self.successful_requests > 0 else 0
            )
            
            # Calculate percentiles from recent requests
            recent_latencies = [
                r['latency_ms'] for r in self.request_log
                if r['success']
            ]
            
            if recent_latencies:
                sorted_latencies = sorted(recent_latencies)
                n = len(sorted_latencies)
                p50 = sorted_latencies[int(n * 0.50)]
                p95 = sorted_latencies[int(n * 0.95)]
                p99 = sorted_latencies[int(n * 0.99)]
            else:
                p50 = p95 = p99 = 0
            
            return {
                'total_requests': self.total_requests,
                'successful_requests': self.successful_requests,
                'failed_requests': self.failed_requests,
                'success_rate': (
                    self.successful_requests / self.total_requests
                    if self.total_requests > 0 else 0
                ),
                'avg_latency_ms': avg_latency,
                'p50_latency_ms': p50,
                'p95_latency_ms': p95,
                'p99_latency_ms': p99,
                'total_retries': self.retries_count,
                'total_failovers': self.failovers_count,
                'current_replica': self.replicas[self.current_replica_idx].address
            }
    
    def get_request_log(self) -> List[dict]:
        """Get the full request log."""
        return list(self.request_log)
    
    def close(self):
        """Close all connections."""
        for channel in self.channels.values():
            channel.close()
        self.channels.clear()
        self.stubs.clear()


def create_client(
    hosts: Optional[List[str]] = None,
    base_port: int = 50051,
    num_replicas: int = 2
) -> RenderingClient:
    """
    Factory function to create a rendering client.
    
    Args:
        hosts: List of host addresses (default: localhost for all)
        base_port: Base port number for replicas
        num_replicas: Number of replicas
        
    Returns:
        Configured RenderingClient instance
    """
    if hosts is None:
        hosts = ['localhost'] * num_replicas
    
    replicas = [
        ReplicaEndpoint(
            host=hosts[i] if i < len(hosts) else 'localhost',
            port=base_port + i,
            priority=i
        )
        for i in range(num_replicas)
    ]
    
    return RenderingClient(replicas)


if __name__ == '__main__':
    # Simple test
    client = create_client()
    
    # Check health of all replicas
    for replica in client.replicas:
        response = client.health_check(replica.address)
        if response:
            print(f"{replica.address}: Healthy={response.healthy}, "
                  f"Frames={response.frames_rendered}")
        else:
            print(f"{replica.address}: Unreachable")
    
    client.close()
