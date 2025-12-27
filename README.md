# Parallel Deferred Renderer

A high-performance OpenGL deferred rendering engine with fault-tolerant distributed capabilities via gRPC.

![OpenGL](https://img.shields.io/badge/OpenGL-3.3+-blue)
![C++](https://img.shields.io/badge/C++-17-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![gRPC](https://img.shields.io/badge/gRPC-1.60+-orange)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Building the Renderer](#building-the-renderer)
- [Phase 3: Fault-Tolerant Distributed System](#phase-3-fault-tolerant-distributed-system)
- [Performance Results](#performance-results)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

This project implements a **Parallel Deferred Renderer** using modern OpenGL techniques. The rendering pipeline separates geometry processing from lighting calculations, enabling efficient handling of multiple light sources.

**Phase 3** extends the renderer into a **fault-tolerant distributed system** using gRPC, with:
- Multiple replicas for high availability
- Automatic failover (sub-second recovery)
- Real-time performance metrics
- Optional Spark streaming integration

---

## Features

### Core Renderer
- **Deferred Rendering Pipeline**: G-Buffer with position, normal, and albedo textures
- **Multiple Light Sources**: Efficient handling of many dynamic lights
- **Model Loading**: Assimp-based 3D model import (OBJ, FBX, etc.)
- **Interactive Camera**: WASD movement, mouse look
- **ImGui Interface**: Real-time parameter adjustment

### Distributed System (Phase 3)
- **gRPC Service**: Wraps renderer with RPC interface
- **2+ Replica Support**: Run multiple server instances
- **Automatic Failover**: Client seamlessly switches on failure
- **30ms Recovery Time**: Near-instant failure recovery
- **Performance Metrics**: Throughput, latency (P50/P95/P99), success rate
- **Spark Streaming**: Optional micro-batch processing at 30 FPS

---

## Project Structure

```
Parallel-Deferred-Renderer/
├── src/                          # C++ source code
│   ├── camera/                   # Camera system
│   ├── lighting/                 # Light management
│   ├── mesh/                     # Mesh/model handling
│   ├── renderer/                 # Core rendering pipeline
│   └── resources/                # Resource management
├── resources/                    # Assets
│   ├── models/                   # 3D models
│   ├── shaders/                  # GLSL shaders
│   └── textures/                 # Texture files
├── api/                          # Third-party libraries
│   ├── assimp/                   # Model loading
│   ├── glad/                     # OpenGL loader
│   ├── glfw/                     # Window management
│   ├── glm/                      # Math library
│   ├── imgui/                    # GUI
│   └── stb/                      # Image loading
├── phase3_ha/                    # Distributed system (Phase 3)
│   ├── demo_native_ha.py         # Main HA demo
│   ├── rendering_server_native.py # gRPC server
│   ├── rendering_client.py       # HA client with failover
│   ├── performance_analysis.py   # Metrics & graphs
│   ├── grpc_spark_streaming.py   # Spark streaming
│   └── protos/                   # Protocol buffers
├── build_Debug/                  # Debug build output
├── CMakeLists.txt                # Build configuration
└── README.md                     # This file
```

---

## Prerequisites

### For Building the Renderer

| Requirement | Version |
|-------------|---------|
| CMake | 3.10+ |
| C++ Compiler | Visual Studio 2019+ or MinGW |
| OpenGL | 3.3+ |

### For Phase 3 Distributed System

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| pip | Latest |

---

## Quick Start

### Option 1: Run the Standalone Renderer

```batch
# Build and run the renderer
build_and_run.bat Debug --run
```

### Option 2: Run the Distributed HA Demo (Phase 3)

```batch
# Navigate to Phase 3 directory
cd phase3_ha

# Install dependencies
pip install -r requirements.txt

# Run the HA demo with 2 replicas
python demo_native_ha.py
```

---

## Building the Renderer

### Windows (Visual Studio)

```batch
# Debug build
build_and_run.bat Debug

# Release build with clean
build_and_run.bat Release --clean

# Build and run immediately
build_and_run.bat Debug --run
```

### Manual CMake Build

```batch
# Create build directory
mkdir build_Debug
cd build_Debug

# Configure
cmake .. -G "Visual Studio 17 2022" -A x64

# Build
cmake --build . --config Debug

# Run
Debug\Parallel-Deferred-Renderer.exe
```

---

## Phase 3: Fault-Tolerant Distributed System

Phase 3 wraps the renderer in a gRPC service with high-availability features.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                                │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  Load Generator │  │ Performance     │                   │
│  │  (60+ seconds)  │  │ Analyzer        │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           └──────────┬─────────┘                             │
│                      ▼                                       │
│           ┌─────────────────────┐                           │
│           │   RenderingClient   │                           │
│           │   (Auto-Failover)   │                           │
│           └──────────┬──────────┘                           │
└──────────────────────┼───────────────────────────────────────┘
                       │ gRPC
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐
   │ Replica 1 │ │ Replica 2 │ │ Replica N │
   │ Port 50051│ │ Port 50052│ │    ...    │
   │ (Primary) │ │ (Standby) │ │           │
   └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
         │             │             │
         └─────────────┼─────────────┘
                       ▼
              ┌───────────────┐
              │  C++ Renderer │
              │  (OpenGL)     │
              └───────────────┘
```

### Quick Start Commands

```batch
cd phase3_ha

# 1. Install dependencies
pip install -r requirements.txt

# 2. Run HA demo (2 replicas with automatic failover)
python demo_native_ha.py

# 3. Run performance analysis (60+ seconds, generates graphs)
python performance_analysis.py --duration 120 --rate 30

# 4. Run Spark streaming demo
python grpc_spark_streaming.py
```

### Available Scripts

| Script | Description |
|--------|-------------|
| `demo_native_ha.py` | Main HA demo with 2 replicas and failover test |
| `performance_analysis.py` | Collects metrics, generates CSV/JSON/PNG |
| `grpc_spark_streaming.py` | Frame streaming at 30 FPS with micro-batches |
| `rendering_server_native.py` | gRPC server wrapping C++ renderer |
| `rendering_client.py` | Client with auto-retry and failover |
| `generate_report_pdf.py` | Generates PDF report from metrics |

### Command Reference

#### Run HA Demo
```batch
python demo_native_ha.py
```
- Starts 2 renderer replicas on ports 50051 and 50052
- Tests automatic failover by killing primary replica
- Verifies recovery to secondary replica

#### Run Performance Analysis
```batch
# Default: 60 seconds, 10 requests/sec
python performance_analysis.py

# Custom: 120 seconds, 30 requests/sec
python performance_analysis.py --duration 120 --rate 30
```

**Output files in `performance_results/`:**
- `request_events_*.csv` - All request timestamps and latencies
- `window_metrics_*.csv` - Per-second throughput and latency stats
- `failure_events_*.csv` - Failure and recovery timestamps
- `performance_graphs_*.png` - Latency and throughput plots
- `recovery_times_*.png` - Recovery time per failure
- `summary_*.json` - Aggregate statistics

#### Run Spark Streaming
```batch
python grpc_spark_streaming.py
```
- Streams frames at ~30 FPS
- Uses micro-batch processing
- Outputs frame statistics

#### Generate PDF Report
```batch
python generate_report_pdf.py
```
- Generates `Phase3_Report.pdf`
- Includes all graphs and metrics

---

## Performance Results

### Typical Results (120-second test)

| Metric | Value |
|--------|-------|
| Total Requests | 3,438 |
| Success Rate | 99.21% |
| Average Latency | 28.5 ms |
| P50 Latency | 26.3 ms |
| P95 Latency | 45.2 ms |
| P99 Latency | 68.7 ms |
| Average Throughput | 28.6 req/s |
| Recovery Time | 30 ms |

### Streaming Performance

| Metric | Value |
|--------|-------|
| Frame Rate | 29.3 FPS |
| Frame Latency | 1.4 ms |
| Batch Size | 10 frames |

---

## Troubleshooting

### Renderer Issues

**Black/blank window:**
- Ensure working directory is project root
- Check that resources folder exists with models/shaders

**CMake errors:**
- Verify CMake 3.10+ is installed
- Check Visual Studio is properly configured

**OpenGL errors:**
- Update graphics drivers
- Verify OpenGL 3.3+ support

### Phase 3 Issues

**gRPC connection refused:**
```batch
# Check if server is running
netstat -an | findstr 50051
```

**Python import errors:**
```batch
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Renderer not launching:**
- Ensure `build_Debug/Debug/Parallel-Deferred-Renderer.exe` exists
- Build the renderer first: `build_and_run.bat Debug`

**Spark errors on Windows:**
- Spark streaming gracefully degrades on Windows
- Core functionality works without Spark

---

## Controls (Renderer)

| Key | Action |
|-----|--------|
| W/A/S/D | Move camera |
| Mouse | Look around |
| ESC | Exit |
| F1 | Toggle ImGui |

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- OpenGL for graphics rendering
- gRPC for distributed communication
- Assimp for model loading
- ImGui for GUI framework
