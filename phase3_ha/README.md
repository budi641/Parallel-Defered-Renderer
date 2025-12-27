# Phase 3: Resilience & High-Availability Integration

## Overview

This module implements fault-tolerant distributed rendering for the Parallel Deferred Renderer project. It wraps the rendering engine in a gRPC service with automatic failover, continuous load handling, and comprehensive performance metrics.

## Features

### ✅ Mandatory Requirements

1. **Distributed Service with Replication**
   - gRPC-based rendering service
   - 2+ replica instances running simultaneously
   - Automatic request routing to healthy replicas
   - 60+ seconds continuous operation

2. **Fault Tolerance**
   - Service crash detection and recovery
   - Automatic failover (no manual intervention)
   - Network disruption handling
   - Auto-restart of failed replicas

3. **Performance Analysis**
   - Real-time metrics collection
   - Throughput (req/sec) tracking
   - Latency percentiles (P50, P95, P99)
   - Recovery time measurement
   - CSV export for graphing

4. **Input Load Generator**
   - Configurable request rate
   - Camera animation simulation
   - 60+ second streaming
   - Comprehensive logging

### 🎁 Bonus Feature

5. **Spark Structured Streaming Integration**
   - Micro-batch processing
   - gRPC calls per micro-batch
   - Fault-tolerant batch processing

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Application                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Load     │  │   Metrics   │  │     Auto-Retry/         │  │
│  │  Generator  │  │  Collector  │  │     Failover Client     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ gRPC
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Replica Manager                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Health Monitoring                          ││
│  │  • Periodic health checks (2s interval)                      ││
│  │  • Failure detection (3 consecutive failures)                ││
│  │  • Auto-restart on failure                                   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Replica 1     │ │   Replica 2     │ │   Replica N     │
│   (Port 50051)  │ │   (Port 50052)  │ │   (Port 5005N)  │
│                 │ │                 │ │                 │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
│  │  gRPC     │  │ │  │  gRPC     │  │ │  │  gRPC     │  │
│  │  Server   │  │ │  │  Server   │  │ │  │  Server   │  │
│  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
│  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │
│  │ Simulated │  │ │  │ Simulated │  │ │  │ Simulated │  │
│  │ Renderer  │  │ │  │ Renderer  │  │ │  │ Renderer  │  │
│  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## File Structure

```
phase3_ha/
├── protos/
│   └── rendering_service.proto    # gRPC service definition
├── rendering_server.py            # gRPC server implementation
├── rendering_client.py            # Client with auto-retry/failover
├── replica_manager.py             # Manages multiple replicas
├── load_generator.py              # Continuous load testing
├── metrics_collector.py           # Performance metrics
├── spark_streaming.py             # Spark integration (bonus)
├── demo.py                        # Main demonstration script
├── generate_proto.py              # Proto code generator
├── requirements.txt               # Python dependencies
├── setup.bat                      # Windows setup script
├── run_demo.bat                   # Standard demo
├── run_demo_extended.bat          # Extended demo
├── run_spark_demo.bat             # Spark streaming demo
├── start_replicas.bat             # Manual replica startup
└── README.md                      # This file
```

## Quick Start

### 1. Setup

```batch
cd phase3_ha
setup.bat
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Generate Protocol Buffer code

### 2. Run Demo

```batch
run_demo.bat
```

This runs a 60-second demonstration with:
- 2 rendering replicas
- 10 requests/second continuous load
- Fault injection at 20s and 40s
- Automatic recovery and failover

### 3. View Results

Results are saved to `demo_output/`:
- `performance_report.txt` - Human-readable summary
- `full_metrics.json` - Complete metrics data
- `time_series.csv` - For plotting graphs
- `failure_events.csv` - Fault/recovery timeline

## Usage

### Running Individual Components

#### Start Rendering Servers
```bash
python rendering_server.py --port 50051 --replica-id replica-1
python rendering_server.py --port 50052 --replica-id replica-2
```

#### Run Load Test
```bash
python load_generator.py --duration 60 --rate 10 --base-port 50051
```

#### Full Demo with Custom Settings
```bash
python demo.py \
    --num-replicas 2 \
    --duration 120 \
    --rate 15 \
    --faults 30,60,90 \
    --output-dir my_results
```

### Spark Streaming Mode
```bash
python demo.py --mode spark --batch-interval 5 --duration 60
```

## API Reference

### gRPC Service

```protobuf
service RenderingService {
    rpc RenderFrame(RenderRequest) returns (RenderResponse);
    rpc StreamFrames(stream RenderRequest) returns (stream RenderResponse);
    rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
    rpc GetStats(StatsRequest) returns (StatsResponse);
}
```

### RenderRequest Fields
| Field | Type | Description |
|-------|------|-------------|
| request_id | int64 | Unique request identifier |
| frame_number | int32 | Frame sequence number |
| width, height | int32 | Frame dimensions |
| camera | CameraParams | Camera position/orientation |
| lighting | LightParams | Lighting configuration |
| material | MaterialParams | Material properties |

### RenderResponse Fields
| Field | Type | Description |
|-------|------|-------------|
| frame_data | bytes | Rendered frame pixels |
| latency_ms | float | Total render time |
| replica_id | string | Which replica served this |
| success | bool | Whether render succeeded |

## Fault Injection

The demo supports two types of fault injection:

### 1. Service Crash
Kills a replica process to simulate a crash:
```python
manager.kill_replica("replica-1")
```

### 2. Network Disruption
Simulated through gRPC timeouts and retries.

## Performance Metrics

### Collected Metrics
| Metric | Description |
|--------|-------------|
| Throughput | Requests per second |
| Latency (avg) | Mean response time |
| Latency (P50) | Median response time |
| Latency (P95) | 95th percentile |
| Latency (P99) | 99th percentile |
| Success Rate | % of successful requests |
| Recovery Time | Time to recover from failure |

### Example Output
```
================================================================================
                    PERFORMANCE ANALYSIS REPORT
================================================================================
Test Duration: 60.2 seconds

OVERVIEW
--------------------------------------------------------------------------------
Total Requests:     598
Successful:         590
Failed:             8
Success Rate:       98.66%
Throughput:         9.80 req/sec

LATENCY METRICS
--------------------------------------------------------------------------------
Average:            32.45 ms
P50 (Median):       30.12 ms
P95:                48.67 ms
P99:                62.34 ms

FAULT TOLERANCE
--------------------------------------------------------------------------------
Failure Events:     2
Avg Recovery Time:  2.34 seconds
================================================================================
```

## Graphing Results

The `time_series.csv` file can be used to create graphs:

### Using Python/Matplotlib
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('demo_output/time_series.csv')

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Latency over time
ax1.plot(df['time'], df['avg_latency_ms'], label='Avg Latency')
ax1.plot(df['time'], df['p95_latency_ms'], label='P95 Latency')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Latency (ms)')
ax1.legend()
ax1.set_title('Latency vs Time')

# Throughput over time
ax2.plot(df['time'], df['throughput_rps'])
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Throughput (req/s)')
ax2.set_title('Throughput vs Time')

plt.tight_layout()
plt.savefig('performance_graphs.png')
```

## Requirements

- Python 3.8+
- Windows 10/11 (or Linux/macOS with minor modifications)
- ~100MB disk space for dependencies

### Python Dependencies
- grpcio >= 1.59.0
- grpcio-tools >= 1.59.0
- protobuf >= 4.24.0
- numpy >= 1.24.0
- Pillow >= 10.0.0
- pyspark >= 3.5.0 (optional, for Spark streaming)

## Troubleshooting

### "grpc_tools not found"
```bash
pip install grpcio-tools
```

### "Proto file not found"
Make sure you're running from the `phase3_ha` directory.

### Replicas not starting
Check that ports 50051 and 50052 are available:
```bash
netstat -an | findstr 50051
```

### Performance issues
Reduce the request rate:
```bash
python demo.py --rate 5
```

## License

This project is part of the Parallel Deferred Renderer educational project.

## Authors

Generated as part of Phase 3 implementation for CS parallel computing course.
