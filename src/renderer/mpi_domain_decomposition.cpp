#include "mpi_domain_decomposition.h"
#include <cmath>
#include <algorithm>

MPIDomainDecomposition::MPIDomainDecomposition()
    : numRanks(1), rank(0), globalWidth(0), globalHeight(0), gridX(1), gridY(1), comm(MPI_COMM_WORLD)
{
}

MPIDomainDecomposition::~MPIDomainDecomposition()
{
}

bool MPIDomainDecomposition::initialize(int globalWidth, int globalHeight, int haloSize, MPI_Comm comm)
{
#ifdef HAVE_MPI
    this->comm = comm;
    this->globalWidth = globalWidth;
    this->globalHeight = globalHeight;
    
    MPI_Comm_size(comm, &numRanks);
    MPI_Comm_rank(comm, &rank);
    
    if (numRanks < 1) {
        return false;
    }
    
    // Calculate optimal 2D grid layout
    float aspectRatio = (float)globalWidth / (float)globalHeight;
    calculateOptimalGrid(numRanks, aspectRatio, gridX, gridY);
    
    // Set up domain
    domain.rank = rank;
    domain.haloSize = haloSize;
    
    // Calculate domain boundaries
    calculateDomain();
    
    return true;
#else
    // MPI not available - single rank mode
    this->comm = comm;
    this->globalWidth = globalWidth;
    this->globalHeight = globalHeight;
    numRanks = 1;
    rank = 0;
    gridX = 1;
    gridY = 1;
    
    domain.rank = 0;
    domain.haloSize = haloSize;
    domain.localWidth = globalWidth;
    domain.localHeight = globalHeight;
    domain.totalWidth = globalWidth + 2 * haloSize;
    domain.totalHeight = globalHeight + 2 * haloSize;
    domain.offsetX = 0;
    domain.offsetY = 0;
    domain.northRank = MPI_PROC_NULL;
    domain.southRank = MPI_PROC_NULL;
    domain.eastRank = MPI_PROC_NULL;
    domain.westRank = MPI_PROC_NULL;
    domain.viewportX = 0;
    domain.viewportY = 0;
    domain.viewportWidth = globalWidth;
    domain.viewportHeight = globalHeight;
    
    return true;
#endif
}

void MPIDomainDecomposition::calculateOptimalGrid(int numRanks, float aspectRatio, int& gridX, int& gridY)
{
    // Find factors of numRanks that best match aspect ratio
    gridX = 1;
    gridY = numRanks;
    float bestRatio = std::abs((float)gridX / (float)gridY - aspectRatio);
    
    for (int x = 1; x <= numRanks; ++x) {
        if (numRanks % x == 0) {
            int y = numRanks / x;
            float ratio = std::abs((float)x / (float)y - aspectRatio);
            if (ratio < bestRatio) {
                bestRatio = ratio;
                gridX = x;
                gridY = y;
            }
        }
    }
}

void MPIDomainDecomposition::calculateDomain()
{
#ifdef HAVE_MPI
    // Calculate position in 2D grid
    int gridPosX = rank % gridX;
    int gridPosY = rank / gridX;
    
    // Calculate local domain size (without halo)
    int tileWidth = globalWidth / gridX;
    int tileHeight = globalHeight / gridY;
    
    // Handle remainder pixels
    int remainderX = globalWidth % gridX;
    int remainderY = globalHeight % gridY;
    
    // Distribute remainder pixels to first few ranks
    if (gridPosX < remainderX) {
        tileWidth++;
    }
    if (gridPosY < remainderY) {
        tileHeight++;
    }
    
    // Calculate offset in global coordinates
    domain.offsetX = 0;
    for (int i = 0; i < gridPosX; ++i) {
        int w = globalWidth / gridX;
        if (i < remainderX) w++;
        domain.offsetX += w;
    }
    
    domain.offsetY = 0;
    for (int i = 0; i < gridPosY; ++i) {
        int h = globalHeight / gridY;
        if (i < remainderY) h++;
        domain.offsetY += h;
    }
    
    // Set local dimensions (without halo)
    domain.localWidth = tileWidth;
    domain.localHeight = tileHeight;
    
    // Set total dimensions (with halo)
    domain.totalWidth = domain.localWidth + 2 * domain.haloSize;
    domain.totalHeight = domain.localHeight + 2 * domain.haloSize;
    
    // Calculate neighbor ranks
    domain.northRank = (gridPosY > 0) ? (rank - gridX) : MPI_PROC_NULL;
    domain.southRank = (gridPosY < gridY - 1) ? (rank + gridX) : MPI_PROC_NULL;
    domain.eastRank = (gridPosX < gridX - 1) ? (rank + 1) : MPI_PROC_NULL;
    domain.westRank = (gridPosX > 0) ? (rank - 1) : MPI_PROC_NULL;
#else
    // Single rank mode - no decomposition needed
    domain.offsetX = 0;
    domain.offsetY = 0;
    domain.localWidth = globalWidth;
    domain.localHeight = globalHeight;
    domain.totalWidth = globalWidth + 2 * domain.haloSize;
    domain.totalHeight = globalHeight + 2 * domain.haloSize;
    domain.northRank = MPI_PROC_NULL;
    domain.southRank = MPI_PROC_NULL;
    domain.eastRank = MPI_PROC_NULL;
    domain.westRank = MPI_PROC_NULL;
#endif
    
    // Calculate viewport for OpenGL (local domain without halo)
    domain.viewportX = domain.offsetX;
    domain.viewportY = domain.offsetY;
    domain.viewportWidth = domain.localWidth;
    domain.viewportHeight = domain.localHeight;
}

bool MPIDomainDecomposition::globalToLocal(int globalX, int globalY, int& localX, int& localY) const
{
    // Check if within local domain (including halo)
    if (globalX < domain.offsetX - domain.haloSize || 
        globalX >= domain.offsetX + domain.localWidth + domain.haloSize ||
        globalY < domain.offsetY - domain.haloSize || 
        globalY >= domain.offsetY + domain.localHeight + domain.haloSize) {
        localX = -1;
        localY = -1;
        return false;
    }
    
    // Convert to local coordinates (with halo offset)
    localX = globalX - (domain.offsetX - domain.haloSize);
    localY = globalY - (domain.offsetY - domain.haloSize);
    
    return true;
}

void MPIDomainDecomposition::localToGlobal(int localX, int localY, int& globalX, int& globalY) const
{
    globalX = localX + (domain.offsetX - domain.haloSize);
    globalY = localY + (domain.offsetY - domain.haloSize);
}

bool MPIDomainDecomposition::isInHalo(int localX, int localY) const
{
    return (localX < domain.haloSize || 
            localX >= domain.localWidth + domain.haloSize ||
            localY < domain.haloSize || 
            localY >= domain.localHeight + domain.haloSize);
}

// ============================================
// Helper functions for MPI datatypes
// ============================================

#ifdef HAVE_MPI
namespace {
    MPI_Datatype getMPIDatatype(float) { return MPI_FLOAT; }
    MPI_Datatype getMPIDatatype(double) { return MPI_DOUBLE; }
    MPI_Datatype getMPIDatatype(int) { return MPI_INT; }
    MPI_Datatype getMPIDatatype(unsigned int) { return MPI_UNSIGNED; }
    MPI_Datatype getMPIDatatype(char) { return MPI_CHAR; }
    MPI_Datatype getMPIDatatype(unsigned char) { return MPI_UNSIGNED_CHAR; }
}
#endif

// ============================================
// Point-to-Point Communication (Blocking)
// ============================================

template<typename T>
void MPIDomainDecomposition::send(const T* sendBuffer, int count, int destRank, int tag) const
{
#ifdef HAVE_MPI
    if (destRank == MPI_PROC_NULL) return;
    MPI_Send(sendBuffer, count, getMPIDatatype(T()), destRank, tag, comm);
#else
    (void)sendBuffer; (void)count; (void)destRank; (void)tag;
#endif
}

template<typename T>
int MPIDomainDecomposition::recv(T* recvBuffer, int count, int sourceRank, int tag) const
{
#ifdef HAVE_MPI
    if (sourceRank == MPI_PROC_NULL) return 0;
    MPI_Status status;
    MPI_Recv(recvBuffer, count, getMPIDatatype(T()), 
             sourceRank == -1 ? MPI_ANY_SOURCE : sourceRank,
             tag == -1 ? MPI_ANY_TAG : tag, comm, &status);
    int receivedCount;
    MPI_Get_count(&status, getMPIDatatype(T()), &receivedCount);
    return receivedCount;
#else
    (void)recvBuffer; (void)count; (void)sourceRank; (void)tag;
    return 0;
#endif
}

// ============================================
// Point-to-Point Communication (Non-Blocking)
// ============================================

template<typename T>
void MPIDomainDecomposition::isend(const T* sendBuffer, int count, int destRank, MPI_Request* request, int tag) const
{
#ifdef HAVE_MPI
    if (destRank == MPI_PROC_NULL) {
        *request = MPI_REQUEST_NULL;
        return;
    }
    MPI_Isend(sendBuffer, count, getMPIDatatype(T()), destRank, tag, comm, request);
#else
    (void)sendBuffer; (void)count; (void)destRank; (void)request; (void)tag;
    *request = MPI_REQUEST_NULL;
#endif
}

template<typename T>
void MPIDomainDecomposition::irecv(T* recvBuffer, int count, int sourceRank, MPI_Request* request, int tag) const
{
#ifdef HAVE_MPI
    if (sourceRank == MPI_PROC_NULL) {
        *request = MPI_REQUEST_NULL;
        return;
    }
    MPI_Irecv(recvBuffer, count, getMPIDatatype(T()),
              sourceRank == -1 ? MPI_ANY_SOURCE : sourceRank,
              tag == -1 ? MPI_ANY_TAG : tag, comm, request);
#else
    (void)recvBuffer; (void)count; (void)sourceRank; (void)request; (void)tag;
    *request = MPI_REQUEST_NULL;
#endif
}

void MPIDomainDecomposition::wait(MPI_Request* request, MPI_Status* status) const
{
#ifdef HAVE_MPI
    if (*request != MPI_REQUEST_NULL) {
        MPI_Wait(request, status == nullptr ? MPI_STATUS_IGNORE : status);
    }
#else
    (void)request; (void)status;
#endif
}

bool MPIDomainDecomposition::test(MPI_Request* request, MPI_Status* status) const
{
#ifdef HAVE_MPI
    if (*request == MPI_REQUEST_NULL) return true;
    int flag;
    MPI_Test(request, &flag, status == nullptr ? MPI_STATUS_IGNORE : status);
    return flag != 0;
#else
    (void)request; (void)status;
    return true;
#endif
}

// ============================================
// Collective Communication
// ============================================

template<typename T>
void MPIDomainDecomposition::bcast(T* buffer, int count, int rootRank) const
{
#ifdef HAVE_MPI
    MPI_Bcast(buffer, count, getMPIDatatype(T()), rootRank, comm);
#else
    (void)buffer; (void)count; (void)rootRank;
#endif
}

template<typename T>
void MPIDomainDecomposition::scatter(const T* sendBuffer, int sendCount, T* recvBuffer, int recvCount, int rootRank) const
{
#ifdef HAVE_MPI
    if (rank == rootRank) {
        MPI_Scatter(sendBuffer, sendCount, getMPIDatatype(T()),
                   recvBuffer, recvCount, getMPIDatatype(T()),
                   rootRank, comm);
    } else {
        MPI_Scatter(nullptr, sendCount, getMPIDatatype(T()),
                   recvBuffer, recvCount, getMPIDatatype(T()),
                   rootRank, comm);
    }
#else
    (void)sendBuffer; (void)sendCount; (void)recvBuffer; (void)recvCount; (void)rootRank;
#endif
}

template<typename T>
void MPIDomainDecomposition::gather(const T* sendBuffer, int sendCount, T* recvBuffer, int recvCount, int rootRank) const
{
#ifdef HAVE_MPI
    if (rank == rootRank) {
        MPI_Gather(sendBuffer, sendCount, getMPIDatatype(T()),
                  recvBuffer, recvCount, getMPIDatatype(T()),
                  rootRank, comm);
    } else {
        MPI_Gather(sendBuffer, sendCount, getMPIDatatype(T()),
                  nullptr, recvCount, getMPIDatatype(T()),
                  rootRank, comm);
    }
#else
    (void)sendBuffer; (void)sendCount; (void)recvBuffer; (void)recvCount; (void)rootRank;
#endif
}

template<typename T>
void MPIDomainDecomposition::reduce(const T* sendBuffer, T* recvBuffer, int count, int op, int rootRank) const
{
#ifdef HAVE_MPI
    if (rank == rootRank) {
        MPI_Reduce(sendBuffer, recvBuffer, count, getMPIDatatype(T()), op, rootRank, comm);
    } else {
        MPI_Reduce(sendBuffer, nullptr, count, getMPIDatatype(T()), op, rootRank, comm);
    }
#else
    (void)sendBuffer; (void)recvBuffer; (void)count; (void)op; (void)rootRank;
#endif
}

template<typename T>
void MPIDomainDecomposition::allreduce(const T* sendBuffer, T* recvBuffer, int count, int op) const
{
#ifdef HAVE_MPI
    MPI_Allreduce(sendBuffer, recvBuffer, count, getMPIDatatype(T()), op, comm);
#else
    (void)sendBuffer; (void)recvBuffer; (void)count; (void)op;
#endif
}

// ============================================
// Halo Exchange Implementation
// ============================================

template<typename T>
void MPIDomainDecomposition::exchangeHaloBlocking(T* imageData, int channels) const
{
#ifdef HAVE_MPI
    const int haloSize = domain.haloSize;
    const int localW = domain.localWidth;
    const int localH = domain.localHeight;
    const int totalW = domain.totalWidth;
    
    // North halo: receive from north rank (which sends its south edge)
    if (domain.northRank != MPI_PROC_NULL) {
        // Receive north halo from north rank (north rank's south edge)
        T* northHalo = imageData + (haloSize - 1) * totalW * channels + haloSize * channels;
        recv(northHalo, localW * channels, domain.northRank, 1);
    }
    // Send our north edge to north rank (for its south halo)
    if (domain.northRank != MPI_PROC_NULL) {
        T* northEdge = imageData + haloSize * totalW * channels + haloSize * channels;
        send(northEdge, localW * channels, domain.northRank, 1);
    }
    
    // South halo: receive from south rank (which sends its north edge)
    if (domain.southRank != MPI_PROC_NULL) {
        // Receive south halo from south rank (south rank's north edge)
        T* southHalo = imageData + (haloSize + localH) * totalW * channels + haloSize * channels;
        recv(southHalo, localW * channels, domain.southRank, 2);
    }
    // Send our south edge to south rank (for its north halo)
    if (domain.southRank != MPI_PROC_NULL) {
        T* southEdge = imageData + (haloSize + localH - 1) * totalW * channels + haloSize * channels;
        send(southEdge, localW * channels, domain.southRank, 2);
    }
    
    // West halo: receive from west rank (which sends its east edge)
    if (domain.westRank != MPI_PROC_NULL) {
        // Receive west halo from west rank (west rank's east edge)
        T* westHalo = imageData + haloSize * totalW * channels + (haloSize - 1) * channels;
        for (int y = 0; y < localH; ++y) {
            recv(westHalo + y * totalW * channels, channels, domain.westRank, 3);
        }
    }
    // Send our west edge to west rank (for its east halo)
    if (domain.westRank != MPI_PROC_NULL) {
        T* westEdge = imageData + haloSize * totalW * channels + haloSize * channels;
        for (int y = 0; y < localH; ++y) {
            send(westEdge + y * totalW * channels, channels, domain.westRank, 3);
        }
    }
    
    // East halo: receive from east rank (which sends its west edge)
    if (domain.eastRank != MPI_PROC_NULL) {
        // Receive east halo from east rank (east rank's west edge)
        T* eastHalo = imageData + haloSize * totalW * channels + (haloSize + localW) * channels;
        for (int y = 0; y < localH; ++y) {
            recv(eastHalo + y * totalW * channels, channels, domain.eastRank, 4);
        }
    }
    // Send our east edge to east rank (for its west halo)
    if (domain.eastRank != MPI_PROC_NULL) {
        T* eastEdge = imageData + haloSize * totalW * channels + (haloSize + localW - 1) * channels;
        for (int y = 0; y < localH; ++y) {
            send(eastEdge + y * totalW * channels, channels, domain.eastRank, 4);
        }
    }
#else
    (void)imageData; (void)channels;
#endif
}

template<typename T>
void MPIDomainDecomposition::exchangeHaloPostNonBlocking(T* imageData, int channels, MPI_Request requests[8]) const
{
#ifdef HAVE_MPI
    const int haloSize = domain.haloSize;
    const int localW = domain.localWidth;
    const int localH = domain.localHeight;
    const int totalW = domain.totalWidth;
    int reqIdx = 0;
    
    // Initialize all requests to NULL
    for (int i = 0; i < 8; ++i) {
        requests[i] = MPI_REQUEST_NULL;
    }
    
    // Post receives first (MPI best practice)
    
    // North halo: receive from north rank (which sends its south edge)
    if (domain.northRank != MPI_PROC_NULL) {
        T* northHalo = imageData + (haloSize - 1) * totalW * channels + haloSize * channels;
        irecv(northHalo, localW * channels, domain.northRank, &requests[reqIdx++], 1);
    }
    
    // South halo: receive from south rank (which sends its north edge)
    if (domain.southRank != MPI_PROC_NULL) {
        T* southHalo = imageData + (haloSize + localH) * totalW * channels + haloSize * channels;
        irecv(southHalo, localW * channels, domain.southRank, &requests[reqIdx++], 2);
    }
    
    // West halo: receive from west rank (which sends its east edge)
    if (domain.westRank != MPI_PROC_NULL) {
        T* westHalo = imageData + haloSize * totalW * channels + (haloSize - 1) * channels;
        for (int y = 0; y < localH; ++y) {
            irecv(westHalo + y * totalW * channels, channels, domain.westRank, &requests[reqIdx++], 3);
        }
    }
    
    // East halo: receive from east rank (which sends its west edge)
    if (domain.eastRank != MPI_PROC_NULL) {
        T* eastHalo = imageData + haloSize * totalW * channels + (haloSize + localW) * channels;
        for (int y = 0; y < localH; ++y) {
            irecv(eastHalo + y * totalW * channels, channels, domain.eastRank, &requests[reqIdx++], 4);
        }
    }
    
    // Post sends
    
    // Send our north edge to north rank (for its south halo)
    if (domain.northRank != MPI_PROC_NULL) {
        T* northEdge = imageData + haloSize * totalW * channels + haloSize * channels;
        isend(northEdge, localW * channels, domain.northRank, &requests[reqIdx++], 1);
    }
    
    // Send our south edge to south rank (for its north halo)
    if (domain.southRank != MPI_PROC_NULL) {
        T* southEdge = imageData + (haloSize + localH - 1) * totalW * channels + haloSize * channels;
        isend(southEdge, localW * channels, domain.southRank, &requests[reqIdx++], 2);
    }
    
    // Send our west edge to west rank (for its east halo)
    if (domain.westRank != MPI_PROC_NULL) {
        T* westEdge = imageData + haloSize * totalW * channels + haloSize * channels;
        for (int y = 0; y < localH; ++y) {
            isend(westEdge + y * totalW * channels, channels, domain.westRank, &requests[reqIdx++], 3);
        }
    }
    
    // Send our east edge to east rank (for its west halo)
    if (domain.eastRank != MPI_PROC_NULL) {
        T* eastEdge = imageData + haloSize * totalW * channels + (haloSize + localW - 1) * channels;
        for (int y = 0; y < localH; ++y) {
            isend(eastEdge + y * totalW * channels, channels, domain.eastRank, &requests[reqIdx++], 4);
        }
    }
#else
    (void)imageData; (void)channels; (void)requests;
#endif
}

void MPIDomainDecomposition::exchangeHaloWaitAll(MPI_Request requests[8]) const
{
#ifdef HAVE_MPI
    MPI_Status statuses[8];
    int count = 0;
    MPI_Request activeRequests[8];
    
    // Collect non-null requests
    for (int i = 0; i < 8; ++i) {
        if (requests[i] != MPI_REQUEST_NULL) {
            activeRequests[count++] = requests[i];
        }
    }
    
    if (count > 0) {
        MPI_Waitall(count, activeRequests, statuses);
    }
#else
    (void)requests;
#endif
}


// Explicit template instantiations for common types
template void MPIDomainDecomposition::send<float>(const float*, int, int, int) const;
template void MPIDomainDecomposition::send<double>(const double*, int, int, int) const;
template void MPIDomainDecomposition::send<int>(const int*, int, int, int) const;
template void MPIDomainDecomposition::send<unsigned char>(const unsigned char*, int, int, int) const;

template int MPIDomainDecomposition::recv<float>(float*, int, int, int) const;
template int MPIDomainDecomposition::recv<double>(double*, int, int, int) const;
template int MPIDomainDecomposition::recv<int>(int*, int, int, int) const;
template int MPIDomainDecomposition::recv<unsigned char>(unsigned char*, int, int, int) const;

template void MPIDomainDecomposition::isend<float>(const float*, int, int, MPI_Request*, int) const;
template void MPIDomainDecomposition::isend<double>(const double*, int, int, MPI_Request*, int) const;
template void MPIDomainDecomposition::isend<int>(const int*, int, int, MPI_Request*, int) const;
template void MPIDomainDecomposition::isend<unsigned char>(const unsigned char*, int, int, MPI_Request*, int) const;

template void MPIDomainDecomposition::irecv<float>(float*, int, int, MPI_Request*, int) const;
template void MPIDomainDecomposition::irecv<double>(double*, int, int, MPI_Request*, int) const;
template void MPIDomainDecomposition::irecv<int>(int*, int, int, MPI_Request*, int) const;
template void MPIDomainDecomposition::irecv<unsigned char>(unsigned char*, int, int, MPI_Request*, int) const;

template void MPIDomainDecomposition::bcast<float>(float*, int, int) const;
template void MPIDomainDecomposition::bcast<double>(double*, int, int) const;
template void MPIDomainDecomposition::bcast<int>(int*, int, int) const;

template void MPIDomainDecomposition::scatter<float>(const float*, int, float*, int, int) const;
template void MPIDomainDecomposition::scatter<double>(const double*, int, double*, int, int) const;
template void MPIDomainDecomposition::scatter<int>(const int*, int, int*, int, int) const;

template void MPIDomainDecomposition::gather<float>(const float*, int, float*, int, int) const;
template void MPIDomainDecomposition::gather<double>(const double*, int, double*, int, int) const;
template void MPIDomainDecomposition::gather<int>(const int*, int, int*, int, int) const;

template void MPIDomainDecomposition::reduce<float>(const float*, float*, int, int, int) const;
template void MPIDomainDecomposition::reduce<double>(const double*, double*, int, int, int) const;
template void MPIDomainDecomposition::reduce<int>(const int*, int*, int, int, int) const;

template void MPIDomainDecomposition::allreduce<float>(const float*, float*, int, int) const;
template void MPIDomainDecomposition::allreduce<double>(const double*, double*, int, int) const;
template void MPIDomainDecomposition::allreduce<int>(const int*, int*, int, int) const;

template void MPIDomainDecomposition::exchangeHaloBlocking<float>(float*, int) const;
template void MPIDomainDecomposition::exchangeHaloBlocking<double>(double*, int) const;
template void MPIDomainDecomposition::exchangeHaloBlocking<unsigned char>(unsigned char*, int) const;

template void MPIDomainDecomposition::exchangeHaloPostNonBlocking<float>(float*, int, MPI_Request*) const;
template void MPIDomainDecomposition::exchangeHaloPostNonBlocking<double>(double*, int, MPI_Request*) const;
template void MPIDomainDecomposition::exchangeHaloPostNonBlocking<unsigned char>(unsigned char*, int, MPI_Request*) const;

