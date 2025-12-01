#ifndef MPI_DOMAIN_DECOMPOSITION_H
#define MPI_DOMAIN_DECOMPOSITION_H

#ifdef HAVE_MPI
#include <mpi.h>
#else
// Dummy MPI definitions when MPI is not available
#define MPI_COMM_WORLD 0
#define MPI_PROC_NULL -1
#define MPI_REQUEST_NULL 0
#define MPI_ANY_SOURCE -1
#define MPI_ANY_TAG -1
#define MPI_STATUS_IGNORE nullptr
typedef int MPI_Comm;
typedef int MPI_Request;
typedef int MPI_Status;
// MPI reduction operations
#define MPI_SUM 0
#define MPI_MAX 1
#define MPI_MIN 2
#define MPI_PROD 3
#endif

#include <vector>
#include <glm/glm.hpp>

/**
 * MPI Domain Decomposition for 2D Grid (Image-Space Rendering)
 * 
 * Implements a 2D grid decomposition where the screen is divided into tiles.
 * Each MPI rank is responsible for rendering a portion of the screen.
 * 
 * Halo/Ghost cells are used for post-processing effects that require
 * neighboring pixel information (SAO, blur, etc.)
 */
class MPIDomainDecomposition {
public:
    // Domain information
    struct Domain {
        int rank;                    // MPI rank ID
        int localWidth;              // Width of local domain (excluding halo)
        int localHeight;             // Height of local domain (excluding halo)
        int totalWidth;              // Total width including halo
        int totalHeight;             // Total height including halo
        int offsetX;                 // X offset in global coordinates
        int offsetY;                 // Y offset in global coordinates
        int haloSize;                // Size of halo region on each side
        
        // Neighbor ranks
        int northRank;               // Rank to the north (or MPI_PROC_NULL)
        int southRank;               // Rank to the south (or MPI_PROC_NULL)
        int eastRank;                // Rank to the east (or MPI_PROC_NULL)
        int westRank;                // Rank to the west (or MPI_PROC_NULL)
        
        // Local viewport (for OpenGL rendering)
        int viewportX;
        int viewportY;
        int viewportWidth;
        int viewportHeight;
    };

    MPIDomainDecomposition();
    ~MPIDomainDecomposition();

    /**
     * Initialize domain decomposition
     * @param globalWidth Total screen width
     * @param globalHeight Total screen height
     * @param haloSize Size of halo region needed (for post-processing)
     * @param comm MPI communicator (default: MPI_COMM_WORLD)
     * @return true if successful
     */
    bool initialize(int globalWidth, int globalHeight, int haloSize, MPI_Comm comm = MPI_COMM_WORLD);

    /**
     * Get domain information for current rank
     */
    const Domain& getDomain() const { return domain; }

    /**
     * Get total number of ranks
     */
    int getNumRanks() const { return numRanks; }

    /**
     * Get current rank ID
     */
    int getRank() const { return rank; }

    /**
     * Check if this is the master rank (rank 0)
     */
    bool isMaster() const { return rank == 0; }

    /**
     * Calculate optimal 2D grid dimensions for given number of ranks
     * @param numRanks Total number of ranks
     * @param aspectRatio Width/Height ratio
     * @param[out] gridX Number of ranks in X direction
     * @param[out] gridY Number of ranks in Y direction
     */
    static void calculateOptimalGrid(int numRanks, float aspectRatio, int& gridX, int& gridY);

    /**
     * Convert global pixel coordinates to local coordinates
     * @param globalX Global X coordinate
     * @param globalY Global Y coordinate
     * @param[out] localX Local X coordinate (or -1 if outside domain)
     * @param[out] localY Local Y coordinate (or -1 if outside domain)
     * @return true if coordinates are within local domain
     */
    bool globalToLocal(int globalX, int globalY, int& localX, int& localY) const;

    /**
     * Convert local pixel coordinates to global coordinates
     * @param localX Local X coordinate
     * @param localY Local Y coordinate
     * @param[out] globalX Global X coordinate
     * @param[out] globalY Global Y coordinate
     */
    void localToGlobal(int localX, int localY, int& globalX, int& globalY) const;

    /**
     * Check if a local coordinate is in the halo region
     */
    bool isInHalo(int localX, int localY) const;

    /**
     * Get MPI communicator
     */
    MPI_Comm getComm() const { return comm; }

    // ============================================
    // MPI Communication Functions
    // ============================================

    /**
     * Blocking Point-to-Point Communication
     * 
     * Send data to a neighbor rank
     * @param sendBuffer Buffer containing data to send
     * @param count Number of elements to send
     * @param destRank Destination rank (or MPI_PROC_NULL)
     * @param tag Message tag
     */
    template<typename T>
    void send(const T* sendBuffer, int count, int destRank, int tag = 0) const;

    /**
     * Blocking Point-to-Point Communication
     * 
     * Receive data from a neighbor rank
     * @param recvBuffer Buffer to store received data
     * @param count Maximum number of elements to receive
     * @param sourceRank Source rank (or MPI_ANY_SOURCE)
     * @param tag Message tag (or MPI_ANY_TAG)
     * @return Number of elements received
     */
    template<typename T>
    int recv(T* recvBuffer, int count, int sourceRank, int tag = 0) const;

    /**
     * Non-Blocking Point-to-Point Communication
     * 
     * Initiate send operation
     * @param sendBuffer Buffer containing data to send
     * @param count Number of elements to send
     * @param destRank Destination rank
     * @param tag Message tag
     * @param[out] request MPI request handle
     */
    template<typename T>
    void isend(const T* sendBuffer, int count, int destRank, MPI_Request* request, int tag = 0) const;

    /**
     * Non-Blocking Point-to-Point Communication
     * 
     * Initiate receive operation
     * @param recvBuffer Buffer to store received data
     * @param count Maximum number of elements to receive
     * @param sourceRank Source rank (or MPI_ANY_SOURCE)
     * @param tag Message tag (or MPI_ANY_TAG)
     * @param[out] request MPI request handle
     */
    template<typename T>
    void irecv(T* recvBuffer, int count, int sourceRank, MPI_Request* request, int tag = 0) const;

    /**
     * Wait for a non-blocking operation to complete
     * @param request MPI request handle
     * @param[out] status MPI status (can be MPI_STATUS_IGNORE)
     */
    void wait(MPI_Request* request, MPI_Status* status = nullptr) const;

    /**
     * Test if a non-blocking operation has completed
     * @param request MPI request handle
     * @param[out] flag True if operation completed
     * @param[out] status MPI status (can be MPI_STATUS_IGNORE)
     * @return true if operation completed
     */
    bool test(MPI_Request* request, MPI_Status* status = nullptr) const;

    // ============================================
    // Collective Communication
    // ============================================

    /**
     * Broadcast data from root to all ranks
     * @param buffer Buffer containing data (in/out)
     * @param count Number of elements
     * @param rootRank Root rank (typically 0)
     */
    template<typename T>
    void bcast(T* buffer, int count, int rootRank = 0) const;

    /**
     * Scatter data from root to all ranks
     * @param sendBuffer Buffer on root containing data for all ranks (only used on root)
     * @param sendCount Number of elements to send to each rank
     * @param recvBuffer Buffer to receive data
     * @param recvCount Number of elements to receive
     * @param rootRank Root rank (typically 0)
     */
    template<typename T>
    void scatter(const T* sendBuffer, int sendCount, T* recvBuffer, int recvCount, int rootRank = 0) const;

    /**
     * Gather data from all ranks to root
     * @param sendBuffer Buffer containing data to send
     * @param sendCount Number of elements to send
     * @param recvBuffer Buffer on root to receive data from all ranks (only used on root)
     * @param recvCount Number of elements to receive from each rank
     * @param rootRank Root rank (typically 0)
     */
    template<typename T>
    void gather(const T* sendBuffer, int sendCount, T* recvBuffer, int recvCount, int rootRank = 0) const;

    /**
     * Reduce data from all ranks to root
     * @param sendBuffer Buffer containing data to send
     * @param recvBuffer Buffer on root to receive reduced data (only used on root)
     * @param count Number of elements
     * @param op MPI reduction operation (e.g., MPI_SUM, MPI_MAX)
     * @param rootRank Root rank (typically 0)
     */
    template<typename T>
    void reduce(const T* sendBuffer, T* recvBuffer, int count, int op, int rootRank = 0) const;

    /**
     * All-reduce: reduce data from all ranks and distribute result to all ranks
     * @param sendBuffer Buffer containing data to send
     * @param recvBuffer Buffer to receive reduced data
     * @param count Number of elements
     * @param op MPI reduction operation (e.g., MPI_SUM, MPI_MAX)
     */
    template<typename T>
    void allreduce(const T* sendBuffer, T* recvBuffer, int count, int op) const;

    // ============================================
    // Halo Exchange (Image Data)
    // ============================================

    /**
     * Exchange halo regions with neighbors (blocking)
     * 
     * Exchanges boundary data with north, south, east, west neighbors
     * @param imageData Local image data (totalWidth x totalHeight)
     * @param channels Number of channels per pixel (e.g., 3 for RGB, 4 for RGBA)
     */
    template<typename T>
    void exchangeHaloBlocking(T* imageData, int channels) const;

    /**
     * Exchange halo regions with neighbors (non-blocking with overlap)
     * 
     * Implements the classical overlap pattern:
     * 1. Post MPI_Irecv for halo
     * 2. Post MPI_Isend
     * 3. Compute interior (while communication happens)
     * 4. MPI_Wait
     * 5. Compute boundaries
     * 
     * @param imageData Local image data (totalWidth x totalHeight)
     * @param channels Number of channels per pixel
     * @param computeInterior Function to compute interior region (called before wait)
     * @param computeBoundaries Function to compute boundary regions (called after wait)
     */
    template<typename T, typename InteriorFunc, typename BoundaryFunc>
    void exchangeHaloNonBlocking(
        T* imageData, 
        int channels,
        InteriorFunc computeInterior,
        BoundaryFunc computeBoundaries
    ) const {
        MPI_Request requests[8];
        
        // Step 1: Post MPI_Irecv for halo
        // Step 2: Post MPI_Isend
        exchangeHaloPostNonBlocking(imageData, channels, requests);
        
        // Step 3: Compute interior (while communication happens)
        computeInterior();
        
        // Step 4: MPI_Wait
        exchangeHaloWaitAll(requests);
        
        // Step 5: Compute boundaries (now that halo data is available)
        computeBoundaries();
    }

    /**
     * Helper: Exchange halo regions (non-blocking, returns requests)
     * Internal use - posts all sends and receives
     */
    template<typename T>
    void exchangeHaloPostNonBlocking(T* imageData, int channels, MPI_Request requests[8]) const;

    /**
     * Helper: Wait for all halo exchange requests
     */
    void exchangeHaloWaitAll(MPI_Request requests[8]) const;

private:
    Domain domain;
    int numRanks;
    int rank;
    int globalWidth;
    int globalHeight;
    int gridX;                      // Number of ranks in X direction
    int gridY;                      // Number of ranks in Y direction
    MPI_Comm comm;

    /**
     * Calculate domain boundaries for current rank
     */
    void calculateDomain();
};

#endif // MPI_DOMAIN_DECOMPOSITION_H

