"""
Phase 3: gRPC Frame Streaming with Spark Micro-Batches

This module provides real-time frame streaming from the C++ renderer
through gRPC, processed via Spark Structured Streaming in micro-batches.

Architecture:
    C++ Renderer -> gRPC Server -> Frame Queue -> Spark Streaming -> Output

Features:
    - gRPC bidirectional streaming for frames
    - Spark micro-batch processing
    - Automatic failover between replicas
    - Real-time frame metrics and analytics
"""

import os
import sys
import time
import json
import logging
import threading
import socket
from typing import Optional, Iterator, Dict, Any, List
from dataclasses import dataclass, asdict
from queue import Queue, Empty
from datetime import datetime
from concurrent import futures

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import grpc
import rendering_service_pb2
import rendering_service_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if PySpark is available (Windows has issues with UnixStreamServer)
SPARK_AVAILABLE = False
try:
    import pyspark
    SPARK_AVAILABLE = True
except (ImportError, AttributeError, Exception) as e:
    logger.warning(f"PySpark not available: {e}")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FrameData:
    """Represents a rendered frame with metadata."""
    frame_id: int
    timestamp: float
    width: int
    height: int
    render_time_ms: float
    replica_id: str
    success: bool
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @staticmethod
    def from_json(json_str: str) -> 'FrameData':
        data = json.loads(json_str)
        return FrameData(**data)


@dataclass 
class StreamMetrics:
    """Metrics for the streaming pipeline."""
    frames_processed: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    failover_count: int = 0
    start_time: float = 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        if self.frames_processed == 0:
            return 0.0
        return self.total_latency_ms / self.frames_processed
    
    @property
    def throughput_fps(self) -> float:
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return 0.0
        return self.frames_processed / elapsed


# ============================================================================
# gRPC Frame Stream Client
# ============================================================================

class GrpcFrameStreamClient:
    """
    Client that streams frames from gRPC rendering servers with failover.
    """
    
    def __init__(self, endpoints: List[str], timeout: float = 5.0):
        self.endpoints = endpoints
        self.timeout = timeout
        self.current_endpoint_idx = 0
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[rendering_service_pb2_grpc.RenderingServiceStub] = None
        self.metrics = StreamMetrics(start_time=time.time())
        self._lock = threading.Lock()
        self._connected = False
        
    def connect(self) -> bool:
        """Connect to the current endpoint."""
        endpoint = self.endpoints[self.current_endpoint_idx]
        
        try:
            self.channel = grpc.insecure_channel(
                endpoint,
                options=[
                    ('grpc.keepalive_time_ms', 10000),
                    ('grpc.keepalive_timeout_ms', 5000),
                ]
            )
            self.stub = rendering_service_pb2_grpc.RenderingServiceStub(self.channel)
            
            # Test connection with health check
            request = rendering_service_pb2.HealthCheckRequest(client_id="stream-client")
            response = self.stub.HealthCheck(request, timeout=self.timeout)
            
            if response.healthy:
                logger.info(f"Connected to {endpoint} (replica: {response.replica_id})")
                self._connected = True
                return True
                
        except Exception as e:
            logger.warning(f"Failed to connect to {endpoint}: {e}")
            
        return False
    
    def failover(self) -> bool:
        """Switch to the next available endpoint."""
        with self._lock:
            original_idx = self.current_endpoint_idx
            
            for i in range(len(self.endpoints)):
                self.current_endpoint_idx = (original_idx + 1 + i) % len(self.endpoints)
                
                if self.connect():
                    self.metrics.failover_count += 1
                    logger.info(f"Failover successful to {self.endpoints[self.current_endpoint_idx]}")
                    return True
            
            logger.error("All endpoints unavailable!")
            return False
    
    def stream_frames(self, target_fps: float = 30.0) -> Iterator[FrameData]:
        """
        Stream frames from the renderer via gRPC.
        
        Yields:
            FrameData objects for each rendered frame
        """
        if not self._connected:
            if not self.connect():
                if not self.failover():
                    return
        
        frame_id = 0
        frame_interval = 1.0 / target_fps
        
        while True:
            try:
                request_time = time.time()
                
                request = rendering_service_pb2.RenderRequest(
                    request_id=frame_id,
                    frame_number=frame_id,
                    width=1920,
                    height=1080,
                    timestamp=int(request_time * 1000)
                )
                
                response = self.stub.RenderFrame(request, timeout=self.timeout)  # type: ignore
                
                response_time = time.time()
                latency_ms = (response_time - request_time) * 1000
                
                # Update metrics
                self.metrics.frames_processed += 1
                self.metrics.total_latency_ms += latency_ms
                self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency_ms)
                self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, latency_ms)
                
                frame = FrameData(
                    frame_id=frame_id,
                    timestamp=response_time,
                    width=response.width,
                    height=response.height,
                    render_time_ms=response.total_time_ms,
                    replica_id=response.replica_id,
                    success=response.success
                )
                
                yield frame
                
                frame_id += 1
                
                # Maintain target FPS
                elapsed = time.time() - request_time
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                    
            except grpc.RpcError as e:
                logger.warning(f"gRPC error: {e}")
                self._connected = False
                
                if not self.failover():
                    logger.error("Stream ended - no replicas available")
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current streaming metrics."""
        return {
            'frames_processed': self.metrics.frames_processed,
            'avg_latency_ms': self.metrics.avg_latency_ms,
            'min_latency_ms': self.metrics.min_latency_ms if self.metrics.min_latency_ms != float('inf') else 0,
            'max_latency_ms': self.metrics.max_latency_ms,
            'throughput_fps': self.metrics.throughput_fps,
            'failover_count': self.metrics.failover_count,
            'current_endpoint': self.endpoints[self.current_endpoint_idx]
        }


# ============================================================================
# Socket-based Frame Source for Spark
# ============================================================================

class FrameSocketServer:
    """
    Socket server that receives frames from gRPC and forwards to Spark.
    
    Spark Structured Streaming can connect to this socket to receive
    frame data as a stream of JSON records.
    """
    
    def __init__(self, host: str = 'localhost', port: int = 9999):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_sockets: List[socket.socket] = []
        self.running = False
        self._accept_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
    def start(self):
        """Start the socket server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        # Start accept thread
        self._accept_thread = threading.Thread(target=self._accept_clients, daemon=True)
        self._accept_thread.start()
        
        logger.info(f"Frame socket server started on {self.host}:{self.port}")
        
    def _accept_clients(self):
        """Accept incoming client connections."""
        while self.running and self.server_socket:
            try:
                self.server_socket.settimeout(1.0)
                client, addr = self.server_socket.accept()
                with self._lock:
                    self.client_sockets.append(client)
                logger.info(f"Client connected from {addr}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")
                break
    
    def send_frame(self, frame: FrameData):
        """Send a frame to all connected clients."""
        message = frame.to_json() + "\n"
        data = message.encode('utf-8')
        
        with self._lock:
            dead_sockets = []
            
            for client in self.client_sockets:
                try:
                    client.sendall(data)
                except Exception:
                    dead_sockets.append(client)
            
            # Remove dead connections
            for dead in dead_sockets:
                self.client_sockets.remove(dead)
                try:
                    dead.close()
                except Exception:
                    pass
    
    def stop(self):
        """Stop the socket server."""
        self.running = False
        
        with self._lock:
            for client in self.client_sockets:
                try:
                    client.close()
                except Exception:
                    pass
            self.client_sockets.clear()
        
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
            
        logger.info("Frame socket server stopped")


# ============================================================================
# Spark Streaming Processor
# ============================================================================

class SparkFrameProcessor:
    """
    Processes frame stream using Spark Structured Streaming.
    
    Uses micro-batches to aggregate and analyze frame metrics in real-time.
    """
    
    def __init__(self, socket_host: str = 'localhost', socket_port: int = 9999):
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.spark = None
        self.query = None
        
    def start(self, batch_interval: str = "5 seconds"):
        """
        Start Spark Structured Streaming processing.
        
        Args:
            batch_interval: Micro-batch trigger interval
        """
        if not SPARK_AVAILABLE:
            logger.warning("PySpark not available on this platform (Windows limitation)")
            return False
            
        try:
            from pyspark.sql import SparkSession
            from pyspark.sql.functions import (
                from_json, col, avg, min as spark_min, max as spark_max,
                count, window, current_timestamp
            )
            from pyspark.sql.types import (
                StructType, StructField, IntegerType, DoubleType,
                StringType, BooleanType, LongType
            )
        except (ImportError, AttributeError, Exception) as e:
            logger.error(f"PySpark not available on this platform: {e}")
            logger.info("Continuing without Spark - using simple streaming instead")
            return False
        
        try:
            # Create Spark session
            self.spark = SparkSession.builder \
                .appName("Phase3-FrameStreaming") \
                .master("local[2]") \
                .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoint") \
                .config("spark.driver.memory", "1g") \
                .getOrCreate()
            
            self.spark.sparkContext.setLogLevel("WARN")
            
            # Define schema for frame data
            schema = StructType([
                StructField("frame_id", IntegerType(), True),
                StructField("timestamp", DoubleType(), True),
                StructField("width", IntegerType(), True),
                StructField("height", IntegerType(), True),
                StructField("render_time_ms", DoubleType(), True),
                StructField("replica_id", StringType(), True),
                StructField("success", BooleanType(), True)
            ])
            
            # Create streaming DataFrame from socket
            lines = self.spark.readStream \
                .format("socket") \
                .option("host", self.socket_host) \
                .option("port", self.socket_port) \
                .load()
            
            # Parse JSON and extract fields
            frames = lines.select(
                from_json(col("value"), schema).alias("frame")
            ).select("frame.*")
            
            # Aggregate metrics per micro-batch
            aggregated = frames \
                .withColumn("batch_time", current_timestamp()) \
                .groupBy("replica_id") \
                .agg(
                    count("*").alias("frame_count"),
                    avg("render_time_ms").alias("avg_render_time"),
                    spark_min("render_time_ms").alias("min_render_time"),
                    spark_max("render_time_ms").alias("max_render_time")
                )
            
            # Output to console
            self.query = aggregated.writeStream \
                .outputMode("complete") \
                .format("console") \
                .trigger(processingTime=batch_interval) \
                .start()
            
            logger.info(f"Spark streaming started with {batch_interval} micro-batches")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Spark streaming: {e}")
            return False
    
    def wait_for_termination(self, timeout: Optional[int] = None):
        """Wait for the streaming query to terminate."""
        if self.query:
            self.query.awaitTermination(int(timeout) if timeout is not None else None)
    
    def stop(self):
        """Stop Spark streaming."""
        if self.query:
            self.query.stop()
            self.query = None
        if self.spark:
            self.spark.stop()
            self.spark = None
        logger.info("Spark streaming stopped")


# ============================================================================
# Main Streaming Pipeline
# ============================================================================

class StreamingPipeline:
    """
    Complete streaming pipeline:
    gRPC Renderer -> Frame Socket -> Spark Micro-batches
    """
    
    def __init__(
        self,
        grpc_endpoints: List[str] = ['localhost:50051', 'localhost:50052'],
        socket_port: int = 9999,
        target_fps: float = 30.0,
        batch_interval: str = "5 seconds"
    ):
        self.grpc_client = GrpcFrameStreamClient(grpc_endpoints)
        self.socket_server = FrameSocketServer(port=socket_port)
        self.spark_processor = SparkFrameProcessor(socket_port=socket_port)
        self.target_fps = target_fps
        self.batch_interval = batch_interval
        
        self._running = False
        self._stream_thread: Optional[threading.Thread] = None
        
    def start(self, use_spark: bool = True):
        """Start the streaming pipeline."""
        logger.info("=" * 60)
        logger.info("STARTING STREAMING PIPELINE")
        logger.info("=" * 60)
        
        # Start socket server (for Spark to connect to)
        self.socket_server.start()
        
        # Start Spark streaming (if enabled)
        if use_spark:
            time.sleep(1)  # Give socket server time to start
            if not self.spark_processor.start(self.batch_interval):
                logger.warning("Spark not available, continuing without it")
        
        # Start frame streaming thread
        self._running = True
        self._stream_thread = threading.Thread(target=self._stream_frames, daemon=True)
        self._stream_thread.start()
        
        logger.info("Streaming pipeline started")
        logger.info(f"  Target FPS: {self.target_fps}")
        logger.info(f"  Batch interval: {self.batch_interval}")
        
    def _stream_frames(self):
        """Stream frames from gRPC to socket server."""
        for frame in self.grpc_client.stream_frames(self.target_fps):
            if not self._running:
                break
            
            # Send to socket server (for Spark)
            self.socket_server.send_frame(frame)
            
            # Log periodic stats
            if frame.frame_id > 0 and frame.frame_id % 100 == 0:
                metrics = self.grpc_client.get_metrics()
                logger.info(
                    f"Frame {frame.frame_id}: "
                    f"FPS={metrics['throughput_fps']:.1f}, "
                    f"Latency={metrics['avg_latency_ms']:.1f}ms, "
                    f"Failovers={metrics['failover_count']}"
                )
    
    def stop(self):
        """Stop the streaming pipeline."""
        self._running = False
        
        if self._stream_thread:
            self._stream_thread.join(timeout=2)
            
        self.spark_processor.stop()
        self.socket_server.stop()
        
        # Print final metrics
        metrics = self.grpc_client.get_metrics()
        logger.info("=" * 60)
        logger.info("FINAL STREAMING METRICS")
        logger.info("=" * 60)
        logger.info(f"  Total frames: {metrics['frames_processed']}")
        logger.info(f"  Average FPS: {metrics['throughput_fps']:.1f}")
        logger.info(f"  Avg latency: {metrics['avg_latency_ms']:.1f}ms")
        logger.info(f"  Min latency: {metrics['min_latency_ms']:.1f}ms")
        logger.info(f"  Max latency: {metrics['max_latency_ms']:.1f}ms")
        logger.info(f"  Failovers: {metrics['failover_count']}")
        logger.info("=" * 60)


# ============================================================================
# Standalone Demo (without Spark)
# ============================================================================

def run_simple_stream(endpoints: List[str], duration: float = 60.0):
    """Run a simple frame stream without Spark."""
    
    print()
    print("=" * 60)
    print("SIMPLE gRPC FRAME STREAMING")
    print("=" * 60)
    print(f"Endpoints: {endpoints}")
    print(f"Duration: {duration}s")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 60)
    print()
    
    client = GrpcFrameStreamClient(endpoints)
    start_time = time.time()
    
    try:
        for frame in client.stream_frames(target_fps=30.0):
            if time.time() - start_time > duration:
                break
            
            # Print frame info periodically
            if frame.frame_id % 30 == 0:
                metrics = client.get_metrics()
                print(
                    f"Frame {frame.frame_id:5d} | "
                    f"Replica: {frame.replica_id:12s} | "
                    f"FPS: {metrics['throughput_fps']:5.1f} | "
                    f"Latency: {metrics['avg_latency_ms']:6.1f}ms | "
                    f"Failovers: {metrics['failover_count']}"
                )
                
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    # Final metrics
    metrics = client.get_metrics()
    print()
    print("=" * 60)
    print("FINAL METRICS")
    print("=" * 60)
    print(f"Total frames:  {metrics['frames_processed']}")
    print(f"Average FPS:   {metrics['throughput_fps']:.1f}")
    print(f"Avg latency:   {metrics['avg_latency_ms']:.1f}ms")
    print(f"Failovers:     {metrics['failover_count']}")
    print("=" * 60)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='gRPC Frame Streaming with Spark')
    parser.add_argument('--endpoints', nargs='+', 
                       default=['localhost:50051', 'localhost:50052'],
                       help='gRPC server endpoints')
    parser.add_argument('--duration', type=float, default=60.0,
                       help='Duration in seconds')
    parser.add_argument('--fps', type=float, default=30.0,
                       help='Target frames per second')
    parser.add_argument('--batch-interval', type=str, default='5 seconds',
                       help='Spark micro-batch interval')
    parser.add_argument('--no-spark', action='store_true',
                       help='Run without Spark (simple streaming)')
    parser.add_argument('--socket-port', type=int, default=9999,
                       help='Socket port for Spark connection')
    
    args = parser.parse_args()
    
    if args.no_spark:
        # Simple streaming without Spark
        run_simple_stream(args.endpoints, args.duration)
    else:
        # Full pipeline with Spark
        pipeline = StreamingPipeline(
            grpc_endpoints=args.endpoints,
            socket_port=args.socket_port,
            target_fps=args.fps,
            batch_interval=args.batch_interval
        )
        
        try:
            pipeline.start(use_spark=True)
            time.sleep(args.duration)
        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            pipeline.stop()


if __name__ == '__main__':
    main()
