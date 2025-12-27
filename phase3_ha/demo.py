"""
Phase 3: High Availability Rendering Service
Main Demo Script - Orchestrates the complete fault-tolerant rendering demo

This script demonstrates:
1. Starting multiple rendering replicas
2. Continuous load generation for 60+ seconds
3. Fault injection (killing replicas)
4. Automatic failover and recovery
5. Performance metrics collection and analysis
6. Optional Spark streaming integration
"""

import os
import sys
import time
import json
import argparse
import threading
import signal
import logging
from datetime import datetime
from typing import Optional, List

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from replica_manager import ReplicaManager, ReplicaState
from rendering_client import RenderingClient, create_client, ReplicaEndpoint
from load_generator import LoadGenerator, LoadGeneratorConfig, save_results, print_summary
from metrics_collector import MetricsCollector, generate_performance_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('demo_log.txt')
    ]
)
logger = logging.getLogger(__name__)


class FaultToleranceDemo:
    """
    Complete demonstration of the fault-tolerant rendering system.
    
    This class orchestrates:
    - Starting rendering service replicas
    - Running continuous load tests
    - Injecting various failure types
    - Measuring recovery and performance
    - Generating comprehensive reports
    """
    
    def __init__(
        self,
        num_replicas: int = 2,
        base_port: int = 50051,
        test_duration: float = 60.0,
        requests_per_second: float = 10.0,
        fault_injection_times: Optional[List[float]] = None,
        output_dir: str = "./demo_output"
    ):
        self.num_replicas = num_replicas
        self.base_port = base_port
        self.test_duration = test_duration
        self.requests_per_second = requests_per_second
        self.fault_injection_times = fault_injection_times or [20.0, 40.0]
        self.output_dir = output_dir
        
        self.manager: Optional[ReplicaManager] = None
        self.client: Optional[RenderingClient] = None
        self.metrics: Optional[MetricsCollector] = None
        self.generator: Optional[LoadGenerator] = None
        
        self._shutdown = threading.Event()
        self._fault_injection_thread: Optional[threading.Thread] = None
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def setup(self):
        """Initialize all components."""
        logger.info("=" * 60)
        logger.info("PHASE 3: RESILIENCE & HIGH-AVAILABILITY DEMO")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  - Replicas: {self.num_replicas}")
        logger.info(f"  - Base Port: {self.base_port}")
        logger.info(f"  - Test Duration: {self.test_duration}s")
        logger.info(f"  - Request Rate: {self.requests_per_second} req/s")
        logger.info(f"  - Fault Injection Times: {self.fault_injection_times}")
        logger.info("=" * 60)
        
        # Initialize replica manager
        logger.info("\n[1/4] Starting rendering replicas...")
        self.manager = ReplicaManager(
            base_port=self.base_port,
            num_replicas=self.num_replicas,
            health_check_interval=2.0,
            auto_restart=True
        )
        self.manager.start_replicas()
        
        # Wait for replicas to be healthy
        logger.info("Waiting for replicas to become healthy...")
        time.sleep(5)
        
        # Check replica status
        status = self.manager.get_status()
        logger.info(f"Replica status: {json.dumps(status, indent=2)}")
        
        # Initialize client
        logger.info("\n[2/4] Initializing client...")
        replicas = [
            ReplicaEndpoint(host='localhost', port=self.base_port + i, priority=i)
            for i in range(self.num_replicas)
        ]
        self.client = RenderingClient(replicas)
        
        # Initialize metrics collector
        logger.info("\n[3/4] Initializing metrics collector...")
        self.metrics = MetricsCollector()
        
        # Initialize load generator
        logger.info("\n[4/4] Initializing load generator...")
        config = LoadGeneratorConfig(
            duration_seconds=self.test_duration,
            requests_per_second=self.requests_per_second,
            camera_animation=True,
            output_file=os.path.join(self.output_dir, 'load_test_results.json'),
            csv_output_file=os.path.join(self.output_dir, 'performance_metrics.csv')
        )
        
        # Custom processing function that records metrics
        def custom_sender(frame_number):
            pass  # We'll handle this in the main loop
        
        self.generator = LoadGenerator(self.client, config)
        
        logger.info("\nSetup complete!")
    
    def inject_faults(self):
        """
        Background thread that injects faults at configured times.
        Demonstrates different failure types:
        1. Service crash (kill replica process)
        2. Network disruption simulation (temporary unavailability)
        """
        start_time = time.time()
        fault_index = 0
        
        while not self._shutdown.is_set() and fault_index < len(self.fault_injection_times):
            elapsed = time.time() - start_time
            
            if elapsed >= self.fault_injection_times[fault_index]:
                # Determine fault type
                if fault_index == 0:
                    # First fault: Kill primary replica
                    self._inject_crash_fault()
                else:
                    # Subsequent faults: Kill another replica
                    self._inject_crash_fault(replica_index=fault_index % self.num_replicas)
                
                fault_index += 1
            
            time.sleep(0.5)
    
    def _inject_crash_fault(self, replica_index: int = 0):
        """Inject a crash fault by killing a replica."""
        replica_id = f"replica-{replica_index + 1}"
        
        logger.warning("=" * 60)
        logger.warning(f"FAULT INJECTION: Killing {replica_id}")
        logger.warning("=" * 60)
        
        if self.metrics:
            self.metrics.record_failure_event(
                "SERVICE_CRASH",
                replica_id,
                "Fault injection: replica process killed"
            )
        
        if self.manager:
            self.manager.kill_replica(replica_id)
    
    def run(self):
        """Run the complete demonstration."""
        try:
            self.setup()
            
            # Start fault injection thread
            if self.fault_injection_times:
                self._fault_injection_thread = threading.Thread(
                    target=self.inject_faults,
                    daemon=True
                )
                self._fault_injection_thread.start()
            
            # Run load test
            logger.info("\n" + "=" * 60)
            logger.info("STARTING LOAD TEST")
            logger.info("=" * 60)
            
            start_time = time.time()
            frame_number = 0
            last_progress_time = 0
            
            while not self._shutdown.is_set():
                elapsed = time.time() - start_time
                
                if elapsed >= self.test_duration:
                    break
                
                if not self.generator or not self.client or not self.metrics:
                    logger.error("Components not initialized")
                    break
                
                # Generate and send request
                request = self.generator._generate_request(frame_number)
                
                try:
                    response_start = time.time()
                    response = self.client.render_frame(request)
                    latency = (time.time() - response_start) * 1000
                    
                    # Record metrics
                    self.metrics.record_frame(
                        frame_number=frame_number,
                        latency_ms=latency,
                        success=response.success,
                        replica_id=response.replica_id,
                        geometry_time_ms=response.geometry_time_ms,
                        lighting_time_ms=response.lighting_time_ms,
                        postprocess_time_ms=response.postprocess_time_ms
                    )
                    
                except Exception as e:
                    self.metrics.record_frame(
                        frame_number=frame_number,
                        latency_ms=0,
                        success=False,
                        replica_id="",
                        error=str(e)
                    )
                
                frame_number += 1
                
                # Progress logging every 10 seconds
                if int(elapsed) % 10 == 0 and int(elapsed) != last_progress_time:
                    last_progress_time = int(elapsed)
                    summary = self.metrics.get_summary()
                    logger.info(
                        f"Progress: {elapsed:.0f}s | "
                        f"Requests: {summary['total_requests']} | "
                        f"Success: {summary['success_rate']*100:.1f}% | "
                        f"Throughput: {summary['throughput_rps']:.1f} req/s"
                    )
                
                # Rate limiting
                time.sleep(1.0 / self.requests_per_second)
            
            logger.info("\nLoad test completed!")
            
        except KeyboardInterrupt:
            logger.info("\nInterrupted by user")
        finally:
            self._shutdown.set()
            self.cleanup()
    
    def cleanup(self):
        """Cleanup and generate reports."""
        logger.info("\n" + "=" * 60)
        logger.info("GENERATING REPORTS")
        logger.info("=" * 60)
        
        # Generate performance report
        if self.metrics:
            generate_performance_report(self.metrics, self.output_dir)
        
        # Save manager events
        if self.manager:
            events = self.manager.get_event_log()
            with open(os.path.join(self.output_dir, 'manager_events.json'), 'w') as f:
                json.dump(events, f, indent=2)
            
            # Stop replicas
            self.manager.shutdown()
        
        # Close client
        if self.client:
            self.client.close()
        
        # Print final summary
        if self.metrics:
            summary = self.metrics.get_summary()
            
            print("\n" + "=" * 60)
            print("FINAL RESULTS")
            print("=" * 60)
            print(f"Total Requests:     {summary['total_requests']}")
            print(f"Successful:         {summary['successful_requests']}")
            print(f"Failed:             {summary['failed_requests']}")
            print(f"Success Rate:       {summary['success_rate']*100:.2f}%")
            print(f"Throughput:         {summary['throughput_rps']:.2f} req/sec")
            print("-" * 60)
            print(f"Avg Latency:        {summary['avg_latency_ms']:.2f} ms")
            print(f"P95 Latency:        {summary['p95_latency_ms']:.2f} ms")
            print(f"P99 Latency:        {summary['p99_latency_ms']:.2f} ms")
            print("-" * 60)
            print(f"Failure Events:     {summary['failure_events']}")
            print(f"Avg Recovery Time:  {summary['avg_recovery_time']:.2f} seconds")
            print("=" * 60)
            print(f"\nResults saved to: {self.output_dir}")


def run_with_spark_streaming(args):
    """Run the demo with Spark streaming integration."""
    from spark_streaming import SimpleMicroBatchProcessor, generate_test_requests
    
    logger.info("Running with micro-batch processing...")
    
    # First, start the replicas
    manager = ReplicaManager(
        base_port=args.base_port,
        num_replicas=args.num_replicas
    )
    
    try:
        manager.start_replicas()
        time.sleep(5)  # Wait for replicas
        
        # Run micro-batch processor
        processor = SimpleMicroBatchProcessor(
            batch_interval=args.batch_interval,
            grpc_host='localhost',
            grpc_port=args.base_port
        )
        
        num_requests = int(args.duration * args.rate)
        requests = generate_test_requests(num_requests, args.rate)
        
        processor.run(requests, args.duration)
        
        # Save results
        os.makedirs(args.output_dir, exist_ok=True)
        processor.save_results(os.path.join(args.output_dir, 'spark_results.json'))
        
        # Print summary
        results = processor.get_results()
        successful = [r for r in results if r.get('success', False)]
        
        print("\n" + "=" * 60)
        print("SPARK STREAMING RESULTS")
        print("=" * 60)
        print(f"Total Batches:      {processor._batch_id + 1}")
        print(f"Total Requests:     {len(results)}")
        print(f"Successful:         {len(successful)}")
        print(f"Success Rate:       {len(successful)/len(results)*100:.1f}%" if results else "N/A")
        print("=" * 60)
        
    finally:
        manager.shutdown()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Phase 3: High Availability Rendering Demo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic demo with 2 replicas for 60 seconds
  python demo.py
  
  # Extended demo with fault injection
  python demo.py --duration 120 --faults 30,60,90
  
  # With Spark streaming integration
  python demo.py --mode spark --batch-interval 5
  
  # Higher load test
  python demo.py --rate 20 --duration 180
"""
    )
    
    parser.add_argument('--mode', choices=['standard', 'spark'], default='standard',
                       help='Demo mode (standard or with Spark streaming)')
    parser.add_argument('--num-replicas', type=int, default=2,
                       help='Number of rendering replicas')
    parser.add_argument('--base-port', type=int, default=50051,
                       help='Base port for replicas')
    parser.add_argument('--duration', type=float, default=60.0,
                       help='Test duration in seconds')
    parser.add_argument('--rate', type=float, default=10.0,
                       help='Requests per second')
    parser.add_argument('--faults', type=str, default='20,40',
                       help='Comma-separated fault injection times (seconds)')
    parser.add_argument('--output-dir', type=str, default='./demo_output',
                       help='Output directory for results')
    parser.add_argument('--batch-interval', type=float, default=5.0,
                       help='Spark micro-batch interval (seconds)')
    parser.add_argument('--no-faults', action='store_true',
                       help='Disable fault injection')
    
    args = parser.parse_args()
    
    # Parse fault injection times
    if args.no_faults:
        fault_times = []
    else:
        fault_times = [float(t.strip()) for t in args.faults.split(',') if t.strip()]
    
    # Handle signals
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run demo
    if args.mode == 'spark':
        run_with_spark_streaming(args)
    else:
        demo = FaultToleranceDemo(
            num_replicas=args.num_replicas,
            base_port=args.base_port,
            test_duration=args.duration,
            requests_per_second=args.rate,
            fault_injection_times=fault_times,
            output_dir=args.output_dir
        )
        demo.run()


if __name__ == '__main__':
    main()
