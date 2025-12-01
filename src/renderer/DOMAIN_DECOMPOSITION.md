# MPI Domain Decomposition - 2D Grid Implementation

## Overview

This implementation provides a **2D grid decomposition** for image-space rendering in the parallel deferred renderer. The screen is divided into tiles, with each MPI rank responsible for rendering a portion of the screen.

## Domain Decomposition Strategy

### 2D Grid Layout

- The screen (WIDTH × HEIGHT) is divided into a 2D grid of tiles
- Grid dimensions (gridX × gridY) are calculated to match the screen aspect ratio
- Each rank is assigned one tile of the grid
- Tiles are distributed to minimize aspect ratio mismatch

### Local Domain per Rank

Each rank has:
- **Local domain**: The portion of the screen it renders (excluding halo)
  - `localWidth`: Width of local domain
  - `localHeight`: Height of local domain
  - `offsetX`, `offsetY`: Position in global screen coordinates

- **Total domain**: Local domain + halo regions
  - `totalWidth`: Local width + 2 × haloSize
  - `totalHeight`: Local height + 2 × haloSize

### Halo/Ghost Cells

Halo regions are used for post-processing effects that require neighboring pixel information:

- **SAO (Screen-Space Ambient Occlusion)**: Needs neighboring depth/normal samples
- **Blur effects**: Requires pixels from adjacent regions
- **Edge detection**: Needs boundary information

**Halo size**: Configurable (typically 1-4 pixels depending on post-processing needs)

**Halo regions**:
- **North halo**: Top border (from north neighbor)
- **South halo**: Bottom border (from south neighbor)
- **East halo**: Right border (from east neighbor)
- **West halo**: Left border (from west neighbor)

### Neighbor Communication

Each rank knows its neighbors:
- `northRank`: Rank above (or `MPI_PROC_NULL` if at top edge)
- `southRank`: Rank below (or `MPI_PROC_NULL` if at bottom edge)
- `eastRank`: Rank to the right (or `MPI_PROC_NULL` if at right edge)
- `westRank`: Rank to the left (or `MPI_PROC_NULL` if at left edge)

## Usage Example

```cpp
#include "mpi_domain_decomposition.h"

// Initialize MPI
MPI_Init(&argc, &argv);

// Create domain decomposition
MPIDomainDecomposition domain;
domain.initialize(1280, 720, 2, MPI_COMM_WORLD);  // 1280x720 screen, 2-pixel halo

// Get domain information
const auto& d = domain.getDomain();

// Set OpenGL viewport for local domain
glViewport(d.viewportX, d.viewportY, d.viewportWidth, d.viewportHeight);

// Render local domain
renderLocalDomain(d);

// Exchange halo data with neighbors
exchangeHaloData(d);

// Finalize MPI
MPI_Finalize();
```

## Coordinate Systems

### Global Coordinates
- Origin: Top-left of screen (0, 0)
- Range: [0, WIDTH) × [0, HEIGHT)
- Used for: Final image composition, display

### Local Coordinates
- Origin: Top-left of local domain including halo (-haloSize, -haloSize)
- Range: [-haloSize, localWidth+haloSize) × [-haloSize, localHeight+haloSize)
- Used for: Local rendering, halo exchange

## Grid Calculation

The optimal grid layout is calculated to:
1. Factor the total number of ranks: `gridX × gridY = numRanks`
2. Minimize aspect ratio mismatch: `|gridX/gridY - screenAspectRatio|`
3. Prefer square-like grids when possible

Example:
- 4 ranks, 1280×720 screen (aspect ~1.78)
- Optimal: 2×2 grid (aspect 1.0, closest to 1.78)
- Each rank: 640×360 pixels

## Implementation Details

### File Structure
- `mpi_domain_decomposition.h`: Header with Domain struct and class interface
- `mpi_domain_decomposition.cpp`: Implementation of domain calculation and coordinate conversion

### Key Functions
- `initialize()`: Set up domain decomposition
- `calculateOptimalGrid()`: Find best grid layout
- `calculateDomain()`: Compute local domain boundaries
- `globalToLocal()`: Convert global to local coordinates
- `localToGlobal()`: Convert local to global coordinates
- `isInHalo()`: Check if coordinate is in halo region

## Next Steps

1. **Halo Exchange**: Implement non-blocking MPI communication for halo data
2. **Image Gathering**: Collect rendered tiles from all ranks to rank 0
3. **Rendering Integration**: Modify rendering passes to use local viewports
4. **Performance Measurement**: Add timing for communication vs computation

