# MPI Communication Implementation

## Overview

This document describes the MPI communication functions implemented in `MPIDomainDecomposition` class, covering point-to-point communication, collective operations, and halo exchange with overlap.

## 1. Point-to-Point Communication

### Blocking Operations

#### `send<T>(sendBuffer, count, destRank, tag)`
- **MPI Function**: `MPI_Send`
- Sends data to a specified destination rank
- Blocks until the message is sent
- **Example**:
  ```cpp
  float data[100];
  decomposition.send(data, 100, 1, 0);  // Send 100 floats to rank 1 with tag 0
  ```

#### `recv<T>(recvBuffer, count, sourceRank, tag)`
- **MPI Function**: `MPI_Recv`
- Receives data from a specified source rank
- Blocks until the message is received
- Returns the number of elements received
- **Example**:
  ```cpp
  float buffer[100];
  int received = decomposition.recv(buffer, 100, 0, 0);  // Receive from rank 0
  ```

### Non-Blocking Operations

#### `isend<T>(sendBuffer, count, destRank, request, tag)`
- **MPI Function**: `MPI_Isend`
- Initiates a non-blocking send operation
- Returns immediately with a request handle
- **Example**:
  ```cpp
  float data[100];
  MPI_Request request;
  decomposition.isend(data, 100, 1, &request, 0);
  // Can do other work here
  decomposition.wait(&request);
  ```

#### `irecv<T>(recvBuffer, count, sourceRank, request, tag)`
- **MPI Function**: `MPI_Irecv`
- Initiates a non-blocking receive operation
- Returns immediately with a request handle
- **Example**:
  ```cpp
  float buffer[100];
  MPI_Request request;
  decomposition.irecv(buffer, 100, 0, &request, 0);
  // Can do other work here
  decomposition.wait(&request);
  ```

#### `wait(request, status)`
- **MPI Function**: `MPI_Wait`
- Waits for a non-blocking operation to complete
- Blocks until the operation finishes

#### `test(request, status)`
- **MPI Function**: `MPI_Test`
- Tests if a non-blocking operation has completed
- Returns immediately with completion status
- **Example**:
  ```cpp
  MPI_Request request;
  // ... post non-blocking operation ...
  bool completed = decomposition.test(&request);
  if (completed) {
      // Operation finished
  }
  ```

## 2. Collective Communication

### Broadcast

#### `bcast<T>(buffer, count, rootRank)`
- **MPI Function**: `MPI_Bcast`
- Broadcasts data from root rank to all ranks
- All ranks receive the same data
- **Example**:
  ```cpp
  float config[10];
  if (rank == 0) {
      // Initialize config on root
  }
  decomposition.bcast(config, 10, 0);  // Broadcast from rank 0
  ```

### Scatter

#### `scatter<T>(sendBuffer, sendCount, recvBuffer, recvCount, rootRank)`
- **MPI Function**: `MPI_Scatter`
- Scatters data from root to all ranks
- Each rank receives a portion of the data
- **Example**:
  ```cpp
  float sendData[100];  // Only used on root
  float recvData[25];   // Each rank receives 25 elements
  decomposition.scatter(sendData, 25, recvData, 25, 0);
  ```

### Gather

#### `gather<T>(sendBuffer, sendCount, recvBuffer, recvCount, rootRank)`
- **MPI Function**: `MPI_Gather`
- Gathers data from all ranks to root
- Root receives data from all ranks
- **Example**:
  ```cpp
  float sendData[100];  // Each rank sends this
  float recvData[400];  // Only used on root (4 ranks × 100)
  decomposition.gather(sendData, 100, recvData, 100, 0);
  ```

### Reduce

#### `reduce<T>(sendBuffer, recvBuffer, count, op, rootRank)`
- **MPI Function**: `MPI_Reduce`
- Reduces data from all ranks to root using an operation
- **Operations**: `MPI_SUM`, `MPI_MAX`, `MPI_MIN`, `MPI_PROD`
- **Example**:
  ```cpp
  float localSum = 100.0f;
  float globalSum;
  decomposition.reduce(&localSum, &globalSum, 1, MPI_SUM, 0);
  // Only rank 0 has the correct globalSum
  ```

### All-Reduce

#### `allreduce<T>(sendBuffer, recvBuffer, count, op)`
- **MPI Function**: `MPI_Allreduce`
- Reduces data from all ranks and distributes result to all ranks
- All ranks receive the reduced result
- **Example**:
  ```cpp
  float localSum = 100.0f;
  float globalSum;
  decomposition.allreduce(&localSum, &globalSum, 1, MPI_SUM);
  // All ranks have the correct globalSum
  ```

## 3. Halo Exchange

### Blocking Halo Exchange

#### `exchangeHaloBlocking<T>(imageData, channels)`
- Exchanges boundary (halo) regions with neighboring ranks
- Uses blocking `MPI_Send` and `MPI_Recv`
- **Pattern**:
  1. Send boundary edges to neighbors
  2. Receive halo regions from neighbors
- **Example**:
  ```cpp
  float* imageData = new float[totalWidth * totalHeight * 4];
  decomposition.exchangeHaloBlocking(imageData, 4);  // RGBA image
  ```

### Non-Blocking Halo Exchange with Overlap

#### `exchangeHaloNonBlocking<T>(imageData, channels, computeInterior, computeBoundaries)`
- Implements the classical overlap pattern for communication/computation overlap
- **Pattern**:
  1. **Post MPI_Irecv** for halo regions
  2. **Post MPI_Isend** for boundary edges
  3. **Compute interior** region (while communication happens in background)
  4. **MPI_Wait** for all communication to complete
  5. **Compute boundaries** using received halo data
- **Example**:
  ```cpp
  float* imageData = new float[totalWidth * totalHeight * 4];
  
  auto computeInterior = [&]() {
      // Process interior pixels (don't need halo data)
      for (int y = haloSize; y < localHeight + haloSize; ++y) {
          for (int x = haloSize; x < localWidth + haloSize; ++x) {
              // Process pixel at (x, y)
          }
      }
  };
  
  auto computeBoundaries = [&]() {
      // Process boundary pixels (now have halo data)
      // Process north, south, east, west boundaries
  };
  
  decomposition.exchangeHaloNonBlocking(
      imageData, 4, 
      computeInterior, 
      computeBoundaries
  );
  ```

## 4. Supported Data Types

The template functions support the following C++ types:
- `float` → `MPI_FLOAT`
- `double` → `MPI_DOUBLE`
- `int` → `MPI_INT`
- `unsigned int` → `MPI_UNSIGNED`
- `char` → `MPI_CHAR`
- `unsigned char` → `MPI_UNSIGNED_CHAR`

## 5. Usage Example: Complete Halo Exchange Pattern

```cpp
#include "mpi_domain_decomposition.h"

// Initialize MPI
MPI_Init(&argc, &argv);

// Create domain decomposition
MPIDomainDecomposition decomposition;
decomposition.initialize(1920, 1080, 8, MPI_COMM_WORLD);  // 8-pixel halo

// Allocate image buffer
const auto& domain = decomposition.getDomain();
float* image = new float[domain.totalWidth * domain.totalHeight * 4];

// Non-blocking halo exchange with overlap
decomposition.exchangeHaloNonBlocking<float>(
    image, 4,
    [&]() {
        // Step 3: Compute interior (overlaps with communication)
        for (int y = domain.haloSize; y < domain.localHeight + domain.haloSize; ++y) {
            for (int x = domain.haloSize; x < domain.localWidth + domain.haloSize; ++x) {
                int idx = (y * domain.totalWidth + x) * 4;
                // Process interior pixel
                image[idx] = processPixel(x, y);
            }
        }
    },
    [&]() {
        // Step 5: Compute boundaries (after halo received)
        // Process north boundary
        for (int x = domain.haloSize; x < domain.localWidth + domain.haloSize; ++x) {
            int y = domain.haloSize;
            int idx = (y * domain.totalWidth + x) * 4;
            image[idx] = processPixel(x, y);  // Can use halo data now
        }
        // ... process other boundaries ...
    }
);

MPI_Finalize();
```

## 6. Performance Considerations

1. **Non-blocking operations** allow overlap of computation and communication
2. **Post receives before sends** (MPI best practice) to avoid deadlocks
3. **Halo exchange** is optimized for 2D grid topologies
4. **Template functions** enable type-safe MPI operations

## 7. Requirements Met

✅ **Point-to-Point (Blocking)**:
- `MPI_Send` → `send()`
- `MPI_Recv` → `recv()`

✅ **Point-to-Point (Non-Blocking)**:
- `MPI_Isend` → `isend()`
- `MPI_Irecv` → `irecv()`
- `MPI_Wait` → `wait()`
- `MPI_Test` → `test()`

✅ **Collectives (2 required)**:
- `MPI_Bcast` → `bcast()`
- `MPI_Scatter` → `scatter()`
- `MPI_Gather` → `gather()`
- `MPI_Reduce` → `reduce()`
- `MPI_Allreduce` → `allreduce()`

✅ **Non-Blocking + Overlap Pattern**:
- Classical pattern implemented in `exchangeHaloNonBlocking()`
- 1. Post `MPI_Irecv` for halo
- 2. Post `MPI_Isend`
- 3. Compute interior
- 4. `MPI_Wait`
- 5. Compute boundaries

