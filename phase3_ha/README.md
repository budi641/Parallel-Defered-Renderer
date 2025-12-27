# Phase 3: gRPC Native Renderer with Failover + Streaming + Performance Analysis

High-availability rendering with automatic failover, real-time streaming, and performance metrics.

## Files

| File | Purpose |
|------|---------|
| `demo_native_ha.py` | **Main Demo** - Runs 2 renderer replicas with automatic failover |
| `grpc_spark_streaming.py` | **Streaming** - gRPC frame streaming (with optional Spark) |
| `performance_analysis.py` | **Metrics** - Load generator + performance graphs |
| `rendering_server_native.py` | gRPC server that launches C++ renderer |
| `rendering_client.py` | gRPC client with retry and failover |
| `rendering_service_pb2.py` | Generated protobuf code |
| `rendering_service_pb2_grpc.py` | Generated gRPC stubs |
| `protos/rendering_service.proto` | Protocol buffer definition |

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the HA demo (2 replicas with failover)
```bash
python demo_native_ha.py
```
- Starts the C++ renderer (replica-1)
- **Close the renderer window** to simulate a crash
- A new renderer window (replica-2) automatically spawns!

### 3. Run gRPC streaming
```bash
python grpc_spark_streaming.py --no-spark --duration 60
```

### 4. Run Performance Analysis (with graphs)
```bash
python performance_analysis.py --duration 120 --rate 30
```
- Generates CSV files with all metrics
- Creates PNG graphs with failure/recovery annotations
- Measures recovery time when you kill the renderer

## Architecture

```
+-------------------+     gRPC      +------------------+
|  C++ Renderer     | <-----------> |  Python Client   |
|  (replica-1)      |               |  with Failover   |
+-------------------+               +--------+---------+
         |                                   |
         | dies                              | streams frames
         v                                   v
+-------------------+               +------------------+
|  C++ Renderer     |               |  Spark Streaming |
|  (replica-2)      |               |  (micro-batches) |
+-------------------+               +------------------+
```
