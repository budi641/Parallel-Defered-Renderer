# MPI Performance Experiments

## Overview

This document describes the performance measurement utilities for MPI communication, including latency, bandwidth, strong scaling, and weak scaling experiments.

## A. Latency & Bandwidth Measurements

### Latency Measurement

**Purpose**: Measure the time it takes to send a small message between two processes.

**Method**: Ping-pong (round-trip) test
- Rank 0 sends a message to rank 1
- Rank 1 receives and immediately sends it back
- Rank 0 receives the reply
- **Latency = (Round-trip time) / 2**

**Implementation**: `MPIPerformance::measureLatency()`

**Example**:
```cpp
std::vector<int> messageSizes = {1, 4, 16, 64, 256, 1024}; // bytes
auto results = MPIPerformance::measureLatency(MPI_COMM_WORLD, messageSizes, 1000);
MPIPerformance::printLatencyResults(results);
```

**Output**:
```
Message Size    Latency (μs)      Round-Trip (μs)
---------------------------------------------------
1               2.45              4.90
4               2.48              4.96
16              2.52              5.04
64              2.55              5.10
256             2.60              5.20
1024            2.75              5.50
```

### Bandwidth Measurement

**Purpose**: Measure the data transfer rate for large messages.

**Method**: One-way transfer test
- Rank 0 sends a large message to rank 1
- Rank 1 receives the message
- **Bandwidth = message_size_bytes / (one-way time)**

**Implementation**: `MPIPerformance::measureBandwidth()`

**Example**:
```cpp
std::vector<int> messageSizes = {
    1024,              // 1 KB
    10240,             // 10 KB
    102400,            // 100 KB
    1048576,           // 1 MB
    5242880,           // 5 MB
    10485760           // 10 MB
};
auto results = MPIPerformance::measureBandwidth(MPI_COMM_WORLD, messageSizes, 100);
MPIPerformance::printBandwidthResults(results);
```

**Output**:
```
Message Size    Bandwidth (MB/s)  Transfer Time (μs)
---------------------------------------------------
1024           8500.25           0.12
10240          9200.50           1.11
102400         9500.75           10.78
1048576        9800.00           106.95
5242880        9900.25           529.32
10485760       9950.50           1053.23
```

## B. Strong Scaling

**Definition**: Strong scaling measures how execution time decreases when the number of processors increases while keeping the problem size constant.

**Ideal Behavior**: 
- Execution time should decrease proportionally with the number of processors
- Speedup = T(1) / T(P), where T(P) is time with P processors
- Ideal speedup = P (linear speedup)
- Efficiency = Speedup / P (should be close to 1.0)

**Implementation**: `MPIPerformance::measureStrongScaling()`

**Example**:
```cpp
// Fixed problem size: 1000x1000
auto workFunction = [](int problemSize) {
    // Perform computation
    double sum = 0.0;
    for (int i = 0; i < problemSize; ++i) {
        for (int j = 0; j < problemSize; ++j) {
            sum += compute(i, j);
        }
    }
    return sum;
};

std::vector<int> processorCounts = {1, 2, 4, 8, 16};
auto results = MPIPerformance::measureStrongScaling(
    MPI_COMM_WORLD,
    workFunction,
    1000,  // Fixed problem size
    processorCounts
);
MPIPerformance::printScalingResults(results);
```

**Output**:
```
Processors  Time (s)          Speedup        Efficiency
--------------------------------------------------------
1           10.500000        1.00           1.00
2           5.400000         1.94           0.97
4           2.800000         3.75           0.94
8           1.500000         7.00           0.88
16          0.900000         11.67          0.73
```

**Analysis**:
- Speedup increases but not linearly (due to communication overhead)
- Efficiency decreases as processors increase (Amdahl's law)
- Communication cost becomes significant with more processors

## C. Weak Scaling

**Definition**: Weak scaling measures how execution time changes when both the problem size and number of processors increase proportionally (constant work per processor).

**Ideal Behavior**:
- Execution time should remain constant
- Speedup should be close to 1.0 (ideal weak scaling)
- Efficiency = Speedup (should be close to 1.0)

**Implementation**: `MPIPerformance::measureWeakScaling()`

**Example**:
```cpp
// Problem size scales with processors: baseSize * numProcessors
auto workFunction = [](int problemSize) {
    // Perform computation
    double sum = 0.0;
    for (int i = 0; i < problemSize; ++i) {
        for (int j = 0; j < problemSize; ++j) {
            sum += compute(i, j);
        }
    }
    return sum;
};

std::vector<int> processorCounts = {1, 2, 4, 8, 16};
auto results = MPIPerformance::measureWeakScaling(
    MPI_COMM_WORLD,
    workFunction,
    500,  // Base problem size per processor
    processorCounts
);
MPIPerformance::printScalingResults(results);
```

**Output**:
```
Processors  Time (s)          Speedup        Efficiency
--------------------------------------------------------
1           2.500000         1.00           1.00
2           2.550000         0.98           0.98
4           2.600000         0.96           0.96
8           2.700000         0.93           0.93
16          2.900000         0.86           0.86
```

**Analysis**:
- Execution time remains relatively constant (good weak scaling)
- Small increases due to communication overhead
- Efficiency close to 1.0 indicates good scalability

## Usage

### Running the Test Program

```bash
# Compile the test program
mpicc -o mpi_performance_test mpi_performance_test.cpp mpi_performance.cpp

# Run with 4 processes
mpirun -np 4 ./mpi_performance_test

# Run with 8 processes
mpirun -np 8 ./mpi_performance_test
```

### Integrating into Your Code

```cpp
#include "mpi_performance.h"

// Measure latency
std::vector<int> sizes = {1, 4, 16, 64, 256, 1024};
auto latency = MPIPerformance::measureLatency(MPI_COMM_WORLD, sizes, 1000);

// Measure bandwidth
std::vector<int> largeSizes = {1024, 10240, 102400, 1048576};
auto bandwidth = MPIPerformance::measureBandwidth(MPI_COMM_WORLD, largeSizes, 100);

// Measure strong scaling
auto strongScaling = MPIPerformance::measureStrongScaling(
    MPI_COMM_WORLD,
    myWorkFunction,
    fixedProblemSize,
    {1, 2, 4, 8, 16}
);

// Measure weak scaling
auto weakScaling = MPIPerformance::measureWeakScaling(
    MPI_COMM_WORLD,
    myWorkFunction,
    baseProblemSize,
    {1, 2, 4, 8, 16}
);

// Export to CSV
MPIPerformance::exportToCSV(
    "results.csv",
    latency,
    bandwidth,
    strongScaling,
    weakScaling
);
```

## Results Export

Results can be exported to CSV format for analysis and plotting:

```cpp
MPIPerformance::exportToCSV(
    "mpi_performance_results.csv",
    latencyResults,
    bandwidthResults,
    strongScalingResults,
    weakScalingResults
);
```

The CSV file contains separate sections for:
- Latency Results
- Bandwidth Results
- Strong Scaling Results
- Weak Scaling Results

## Performance Analysis

### Interpreting Results

1. **Latency**:
   - Small latency (< 5 μs) indicates efficient communication
   - Latency should be relatively constant for small messages
   - Increases with message size indicate overhead

2. **Bandwidth**:
   - Higher bandwidth is better
   - Should approach network/hardware limits for large messages
   - Lower bandwidth for small messages is normal (latency dominates)

3. **Strong Scaling**:
   - Speedup < P indicates overhead (communication, load imbalance)
   - Efficiency < 0.8 suggests significant overhead
   - Ideal: linear speedup (speedup = P, efficiency = 1.0)

4. **Weak Scaling**:
   - Time should remain constant (speedup ≈ 1.0)
   - Efficiency close to 1.0 indicates good scalability
   - Increasing time indicates communication overhead

### Common Issues

1. **Low Efficiency in Strong Scaling**:
   - Too much communication relative to computation
   - Load imbalance
   - Sequential bottlenecks (Amdahl's law)

2. **Poor Weak Scaling**:
   - Communication overhead grows with problem size
   - Memory bandwidth limitations
   - Network congestion

3. **High Latency**:
   - Network latency
   - MPI implementation overhead
   - System load

## Notes

- **Even on a single node**, these measurements reveal real MPI overheads
- Communication costs are significant even with shared memory
- Results help identify bottlenecks and optimization opportunities
- Use results to choose optimal processor counts for your workload

## References

- **Latency**: Round-trip time / 2
- **Bandwidth**: Message size / Transfer time
- **Strong Scaling**: Same problem, more processors
- **Weak Scaling**: Problem scales with processors

