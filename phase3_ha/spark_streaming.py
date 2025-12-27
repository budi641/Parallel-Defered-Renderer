"""
Phase 3: High Availability Rendering Service
Spark Structured Streaming Integration (Bonus Feature)

This module implements Spark Structured Streaming integration with
the gRPC rendering service for micro-batch processing of render requests.
"""

import os
import sys
import time
import json
import logging
from typing import Optional, List, Dict
from datetime import datetime
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if PySpark is available
try:
    from pyspark.sql import SparkSession  # type: ignore[import-not-found]
    from pyspark.sql.functions import (  # type: ignore[import-not-found]
        col, udf, struct, lit, current_timestamp, 
        window, count, avg, max as spark_max, min as spark_min
    )
    from pyspark.sql.types import (  # type: ignore[import-not-found]
        StructType, StructField, IntegerType, FloatType, 
        BooleanType, StringType, LongType, BinaryType
    )
    SPARK_AVAILABLE = True
except (ImportError, AttributeError, Exception) as e:
    # AttributeError: PySpark uses Unix sockets which don't exist on Windows
    # ImportError: PySpark not installed
    SPARK_AVAILABLE = False
    logger.warning(f"PySpark not available: {e}")

# Add the generated protobuf path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class SparkStreamingRenderer:
    """
    Spark Structured Streaming integration for the rendering service.
    
    This class implements micro-batch ingestion of render requests,
    processing them through the gRPC service, and collecting results.
    
    Features:
    - Micro-batch processing with configurable batch interval
    - Fault-tolerant processing with checkpointing
    - Integration with gRPC rendering service
    - Real-time metrics aggregation
    """
    
    def __init__(
        self,
        app_name: str = "RenderingStreamProcessor",
        master: str = "local[*]",
        batch_interval: int = 5,  # seconds
        checkpoint_dir: str = "./spark_checkpoints",
        grpc_host: str = "localhost",
        grpc_port: int = 50051
    ):
        if not SPARK_AVAILABLE:
            raise RuntimeError("PySpark is not installed. Install with: pip install pyspark")
        
        self.app_name = app_name
        self.master = master
        self.batch_interval = batch_interval
        self.checkpoint_dir = checkpoint_dir
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port
        
        self.spark: Optional[SparkSession] = None
        self._streaming_query = None
        self._shutdown = threading.Event()
        
        # Schema for render requests
        self.request_schema = StructType([
            StructField("request_id", LongType(), False),
            StructField("frame_number", IntegerType(), False),
            StructField("timestamp", LongType(), False),
            StructField("camera_x", FloatType(), True),
            StructField("camera_y", FloatType(), True),
            StructField("camera_z", FloatType(), True),
            StructField("camera_yaw", FloatType(), True),
            StructField("camera_pitch", FloatType(), True),
            StructField("width", IntegerType(), True),
            StructField("height", IntegerType(), True)
        ])
        
        # Schema for render responses
        self.response_schema = StructType([
            StructField("request_id", LongType(), False),
            StructField("frame_number", IntegerType(), False),
            StructField("success", BooleanType(), False),
            StructField("latency_ms", FloatType(), False),
            StructField("replica_id", StringType(), True),
            StructField("error", StringType(), True)
        ])
    
    def _create_spark_session(self) -> SparkSession:
        """Create and configure the Spark session."""
        return (SparkSession.builder
            .appName(self.app_name)
            .master(self.master)
            .config("spark.sql.streaming.schemaInference", "true")
            .config("spark.sql.shuffle.partitions", "2")
            .config("spark.streaming.stopGracefullyOnShutdown", "true")
            .getOrCreate())
    
    def start(self):
        """Initialize the Spark session."""
        logger.info("Starting Spark session...")
        self.spark = self._create_spark_session()
        if self.spark:
            self.spark.sparkContext.setLogLevel("WARN")
            logger.info(f"Spark session started: {self.spark.version}")
        else:
            logger.error("Failed to create Spark session")
    
    def stop(self):
        """Stop the Spark session and any running queries."""
        self._shutdown.set()
        
        if self._streaming_query:
            logger.info("Stopping streaming query...")
            self._streaming_query.stop()
        
        if self.spark:
            logger.info("Stopping Spark session...")
            self.spark.stop()
            self.spark = None
    
    def create_render_request_stream(self, input_dir: str):
        """
        Create a streaming DataFrame from JSON files in a directory.
        Files should contain render request data.
        """
        if not self.spark:
            self.start()
        
        if not self.spark:
            raise RuntimeError("Failed to initialize Spark session")
        
        return (self.spark.readStream
            .format("json")
            .schema(self.request_schema)
            .option("maxFilesPerTrigger", 10)
            .load(input_dir))
    
    def create_rate_stream(self, rows_per_second: int = 10):
        """
        Create a rate-based streaming source for testing.
        Generates synthetic render requests at specified rate.
        """
        if not self.spark:
            self.start()
        
        if not self.spark:
            raise RuntimeError("Failed to initialize Spark session")
        
        # Create rate stream
        rate_df = (self.spark.readStream
            .format("rate")
            .option("rowsPerSecond", rows_per_second)
            .load())
        
        # Transform to render requests
        import math
        from pyspark.sql.functions import sin, cos  # type: ignore[import-not-found]
        
        return rate_df.select(
            col("value").alias("request_id"),
            col("value").cast(IntegerType()).alias("frame_number"),
            (col("timestamp").cast(LongType())).alias("timestamp"),
            (cos(col("value") * 0.1) * 4).cast(FloatType()).alias("camera_x"),
            lit(1.0).cast(FloatType()).alias("camera_y"),
            (sin(col("value") * 0.1) * 4).cast(FloatType()).alias("camera_z"),
            (col("value") * 0.5 % 360).cast(FloatType()).alias("camera_yaw"),
            lit(0.0).cast(FloatType()).alias("camera_pitch"),
            lit(320).alias("width"),
            lit(240).alias("height")
        )
    
    def process_with_grpc(self, df, output_dir: str, process_func=None):
        """
        Process streaming DataFrame by calling gRPC service for each micro-batch.
        
        Args:
            df: Streaming DataFrame with render requests
            output_dir: Directory to write results
            process_func: Optional custom processing function
        """
        if process_func is None:
            process_func = self._default_process_batch
        
        # Define the foreach batch function
        def foreach_batch_function(batch_df, batch_id):
            if batch_df.isEmpty():
                return
            
            logger.info(f"Processing micro-batch {batch_id} with {batch_df.count()} requests")
            
            # Collect requests and process through gRPC
            requests = batch_df.collect()
            results = process_func(requests, batch_id)
            
            # Write results
            if results and self.spark:
                results_df = self.spark.createDataFrame(results, self.response_schema)
                (results_df.write
                    .mode("append")
                    .json(f"{output_dir}/batch_{batch_id}"))
            
            logger.info(f"Completed micro-batch {batch_id}")
        
        # Start the streaming query
        self._streaming_query = (df.writeStream
            .foreachBatch(foreach_batch_function)
            .option("checkpointLocation", self.checkpoint_dir)
            .trigger(processingTime=f"{self.batch_interval} seconds")
            .start())
        
        return self._streaming_query
    
    def _default_process_batch(self, requests, batch_id) -> List[Dict]:
        """
        Default batch processing function that calls the gRPC service.
        """
        import grpc
        import rendering_service_pb2
        import rendering_service_pb2_grpc
        
        results = []
        
        # Connect to gRPC service
        try:
            channel = grpc.insecure_channel(f"{self.grpc_host}:{self.grpc_port}")
            stub = rendering_service_pb2_grpc.RenderingServiceStub(channel)
            
            for row in requests:
                try:
                    # Create gRPC request
                    camera = rendering_service_pb2.CameraParams(
                        position_x=row.camera_x or 0,
                        position_y=row.camera_y or 1,
                        position_z=row.camera_z or 4,
                        yaw=row.camera_yaw or 0,
                        pitch=row.camera_pitch or 0
                    )
                    
                    request = rendering_service_pb2.RenderRequest(
                        request_id=row.request_id,
                        timestamp=row.timestamp or int(time.time() * 1000),
                        frame_number=row.frame_number,
                        width=row.width or 320,
                        height=row.height or 240,
                        camera=camera,
                        is_streaming=True
                    )
                    
                    # Call gRPC service
                    start_time = time.time()
                    response = stub.RenderFrame(request, timeout=10.0)
                    latency = (time.time() - start_time) * 1000
                    
                    results.append({
                        'request_id': row.request_id,
                        'frame_number': row.frame_number,
                        'success': response.success,
                        'latency_ms': latency,
                        'replica_id': response.replica_id,
                        'error': response.error_message or ""
                    })
                    
                except grpc.RpcError as e:
                    results.append({
                        'request_id': row.request_id,
                        'frame_number': row.frame_number,
                        'success': False,
                        'latency_ms': 0.0,
                        'replica_id': "",
                        'error': str(e)
                    })
            
            channel.close()
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            for row in requests:
                results.append({
                    'request_id': row.request_id,
                    'frame_number': row.frame_number,
                    'success': False,
                    'latency_ms': 0.0,
                    'replica_id': "",
                    'error': str(e)
                })
        
        return results
    
    def aggregate_metrics(self, df):
        """
        Create an aggregation query for real-time metrics.
        """
        return (df
            .withWatermark("timestamp", "10 seconds")
            .groupBy(window(col("timestamp"), "10 seconds"))
            .agg(
                count("*").alias("request_count"),
                avg("latency_ms").alias("avg_latency"),
                spark_max("latency_ms").alias("max_latency"),
                spark_min("latency_ms").alias("min_latency")
            ))
    
    def run_demo(self, duration_seconds: int = 60, output_dir: str = "./spark_output"):
        """
        Run a demo of the Spark streaming integration.
        """
        logger.info(f"Starting Spark streaming demo for {duration_seconds} seconds")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        # Start Spark
        self.start()
        
        # Create rate-based stream
        request_stream = self.create_rate_stream(rows_per_second=5)
        
        # Process with gRPC
        query = self.process_with_grpc(request_stream, output_dir)
        
        # Wait for duration
        try:
            logger.info(f"Streaming for {duration_seconds} seconds...")
            query.awaitTermination(duration_seconds * 1000)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()
        
        logger.info("Demo completed")


class SimpleMicroBatchProcessor:
    """
    A simplified micro-batch processor that doesn't require full Spark.
    Useful for environments where Spark is not available.
    
    This implements the same pattern but using pure Python.
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        batch_interval: float = 5.0,
        grpc_host: str = "localhost",
        grpc_port: int = 50051
    ):
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.grpc_host = grpc_host
        self.grpc_port = grpc_port
        
        self._shutdown = threading.Event()
        self._batch_queue: List[Dict] = []
        self._lock = threading.Lock()
        self._batch_id = 0
        self.results: List[Dict] = []
    
    def add_request(self, request: Dict):
        """Add a request to the current batch."""
        with self._lock:
            self._batch_queue.append(request)
    
    def process_batch(self, requests: List[Dict], batch_id: int) -> List[Dict]:
        """Process a batch of requests through gRPC."""
        import grpc
        import rendering_service_pb2
        import rendering_service_pb2_grpc
        
        results = []
        
        try:
            channel = grpc.insecure_channel(f"{self.grpc_host}:{self.grpc_port}")
            stub = rendering_service_pb2_grpc.RenderingServiceStub(channel)
            
            for req in requests:
                try:
                    camera = rendering_service_pb2.CameraParams(
                        position_x=req.get('camera_x', 0),
                        position_y=req.get('camera_y', 1),
                        position_z=req.get('camera_z', 4)
                    )
                    
                    grpc_request = rendering_service_pb2.RenderRequest(
                        request_id=req.get('request_id', 0),
                        timestamp=int(time.time() * 1000),
                        frame_number=req.get('frame_number', 0),
                        width=req.get('width', 320),
                        height=req.get('height', 240),
                        camera=camera
                    )
                    
                    start_time = time.time()
                    response = stub.RenderFrame(grpc_request, timeout=10.0)
                    latency = (time.time() - start_time) * 1000
                    
                    results.append({
                        'batch_id': batch_id,
                        'request_id': req.get('request_id'),
                        'frame_number': req.get('frame_number'),
                        'success': response.success,
                        'latency_ms': latency,
                        'replica_id': response.replica_id
                    })
                    
                except grpc.RpcError as e:
                    results.append({
                        'batch_id': batch_id,
                        'request_id': req.get('request_id'),
                        'frame_number': req.get('frame_number'),
                        'success': False,
                        'latency_ms': 0,
                        'error': str(e)
                    })
            
            channel.close()
            
        except Exception as e:
            logger.error(f"Batch error: {e}")
        
        return results
    
    def run(self, request_generator, duration_seconds: float = 60):
        """
        Run the micro-batch processor.
        
        Args:
            request_generator: Iterator yielding request dicts
            duration_seconds: How long to run
        """
        start_time = time.time()
        last_batch_time = start_time
        
        logger.info(f"Starting micro-batch processing for {duration_seconds}s")
        
        try:
            for request in request_generator:
                if self._shutdown.is_set():
                    break
                
                elapsed = time.time() - start_time
                if elapsed >= duration_seconds:
                    break
                
                self.add_request(request)
                
                # Check if it's time to process a batch
                if time.time() - last_batch_time >= self.batch_interval:
                    with self._lock:
                        if self._batch_queue:
                            batch = self._batch_queue.copy()
                            self._batch_queue.clear()
                    
                    if batch:
                        logger.info(f"Processing micro-batch {self._batch_id} ({len(batch)} requests)")
                        results = self.process_batch(batch, self._batch_id)
                        self.results.extend(results)
                        self._batch_id += 1
                    
                    last_batch_time = time.time()
            
            # Process remaining requests
            with self._lock:
                if self._batch_queue:
                    batch = self._batch_queue.copy()
                    self._batch_queue.clear()
            
            if batch:
                logger.info(f"Processing final micro-batch {self._batch_id} ({len(batch)} requests)")
                results = self.process_batch(batch, self._batch_id)
                self.results.extend(results)
        
        except Exception as e:
            logger.error(f"Processing error: {e}")
        
        finally:
            logger.info(f"Processed {len(self.results)} requests in {self._batch_id + 1} batches")
    
    def stop(self):
        """Stop the processor."""
        self._shutdown.set()
    
    def get_results(self) -> List[Dict]:
        """Get all processing results."""
        return self.results.copy()
    
    def save_results(self, filepath: str):
        """Save results to JSON."""
        with open(filepath, 'w') as f:
            json.dump({
                'total_batches': self._batch_id + 1,
                'total_requests': len(self.results),
                'results': self.results
            }, f, indent=2)
        
        logger.info(f"Results saved to {filepath}")


def generate_test_requests(count: int = 100, rate: float = 10):
    """Generator for test render requests."""
    import math
    
    for i in range(count):
        angle = i * 0.1
        yield {
            'request_id': i,
            'frame_number': i,
            'camera_x': math.cos(angle) * 4,
            'camera_y': 1.0,
            'camera_z': math.sin(angle) * 4,
            'camera_yaw': math.degrees(angle),
            'camera_pitch': 0,
            'width': 320,
            'height': 240
        }
        time.sleep(1.0 / rate)


def main():
    """Demo of the streaming integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Spark Streaming Renderer')
    parser.add_argument('--mode', choices=['spark', 'simple'], default='simple',
                       help='Processing mode')
    parser.add_argument('--duration', type=int, default=60,
                       help='Duration in seconds')
    parser.add_argument('--rate', type=float, default=5,
                       help='Requests per second')
    parser.add_argument('--batch-interval', type=float, default=5,
                       help='Batch interval in seconds')
    parser.add_argument('--output', type=str, default='./streaming_output',
                       help='Output directory')
    
    args = parser.parse_args()
    
    if args.mode == 'spark':
        if not SPARK_AVAILABLE:
            logger.error("Spark not available. Use --mode simple instead.")
            return
        
        processor = SparkStreamingRenderer(batch_interval=int(args.batch_interval))
        processor.run_demo(args.duration, args.output)
    else:
        # Simple mode
        processor = SimpleMicroBatchProcessor(
            batch_interval=args.batch_interval
        )
        
        num_requests = int(args.duration * args.rate)
        requests = generate_test_requests(num_requests, args.rate)
        
        processor.run(requests, args.duration)
        
        os.makedirs(args.output, exist_ok=True)
        processor.save_results(os.path.join(args.output, 'micro_batch_results.json'))
        
        # Print summary
        results = processor.get_results()
        successful = [r for r in results if r.get('success', False)]
        print(f"\nProcessed {len(results)} requests in {processor._batch_id + 1} batches")
        print(f"Success rate: {len(successful)/len(results)*100:.1f}%" if results else "No results")


if __name__ == '__main__':
    main()
