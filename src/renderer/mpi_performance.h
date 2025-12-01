#ifndef MPI_PERFORMANCE_H
#define MPI_PERFORMANCE_H

#ifdef HAVE_MPI
#include <mpi.h>
#else
// Dummy definitions
#define MPI_COMM_WORLD 0
typedef int MPI_Comm;
typedef int MPI_Request;
typedef int MPI_Status;
#define MPI_REQUEST_NULL 0
#endif

#include <vector>
#include <string>
#include <functional>

/**
 * MPI Performance Measurement Utilities
 * 
 * Provides functions to measure:
 * - Latency (small messages, round-trip time)
 * - Bandwidth (large messages, one-way time)
 * - Strong scaling (same problem size, varying processors)
 * - Weak scaling (problem size scales with processors)
 */
class MPIPerformance {
public:
    struct LatencyResult {
        int messageSize;        // Message size in bytes
        double latency;         // One-way latency in microseconds
        double roundTripTime;   // Round-trip time in microseconds
    };

    struct BandwidthResult {
        int messageSize;        // Message size in bytes
        double bandwidth;        // Bandwidth in MB/s
        double transferTime;     // Transfer time in microseconds
    };

    struct ScalingResult {
        int numRanks;           // Number of MPI ranks
        double executionTime;   // Execution time in seconds
        double speedup;         // Speedup relative to baseline
        double efficiency;      // Efficiency (speedup / numRanks)
    };

    /**
     * Measure latency using ping-pong (round-trip) test
     * 
     * @param comm MPI communicator
     * @param messageSizes Vector of message sizes to test (in bytes)
     * @param iterations Number of iterations per message size
     * @return Vector of latency results
     */
    static std::vector<LatencyResult> measureLatency(
        MPI_Comm comm,
        const std::vector<int>& messageSizes,
        int iterations = 1000
    );

    /**
     * Measure bandwidth using one-way transfer
     * 
     * @param comm MPI communicator
     * @param messageSizes Vector of message sizes to test (in bytes)
     * @param iterations Number of iterations per message size
     * @return Vector of bandwidth results
     */
    static std::vector<BandwidthResult> measureBandwidth(
        MPI_Comm comm,
        const std::vector<int>& messageSizes,
        int iterations = 100
    );

    /**
     * Measure strong scaling
     * 
     * Strong scaling: same problem size, varying number of processors
     * Measures how execution time decreases as processors increase
     * 
     * @param comm MPI communicator
     * @param workFunction Function that performs the work (takes problem size, returns execution time)
     * @param problemSize Fixed problem size (same for all processor counts)
     * @param processorCounts Vector of processor counts to test
     * @return Vector of scaling results
     */
    static std::vector<ScalingResult> measureStrongScaling(
        MPI_Comm comm,
        std::function<double(int problemSize)> workFunction,
        int problemSize,
        const std::vector<int>& processorCounts
    );

    /**
     * Measure weak scaling
     * 
     * Weak scaling: problem size scales with number of processors
     * Measures how execution time changes when work per processor is constant
     * 
     * @param comm MPI communicator
     * @param workFunction Function that performs the work (takes problem size, returns execution time)
     * @param baseProblemSize Base problem size per processor
     * @param processorCounts Vector of processor counts to test
     * @return Vector of scaling results
     */
    static std::vector<ScalingResult> measureWeakScaling(
        MPI_Comm comm,
        std::function<double(int problemSize)> workFunction,
        int baseProblemSize,
        const std::vector<int>& processorCounts
    );

    /**
     * Print latency results to console
     */
    static void printLatencyResults(const std::vector<LatencyResult>& results);

    /**
     * Print bandwidth results to console
     */
    static void printBandwidthResults(const std::vector<BandwidthResult>& results);

    /**
     * Print scaling results to console
     */
    static void printScalingResults(const std::vector<ScalingResult>& results);

    /**
     * Export results to CSV file
     */
    static void exportToCSV(
        const std::string& filename,
        const std::vector<LatencyResult>& latencyResults,
        const std::vector<BandwidthResult>& bandwidthResults,
        const std::vector<ScalingResult>& strongScalingResults,
        const std::vector<ScalingResult>& weakScalingResults
    );

    /**
     * Get high-resolution timer (in seconds)
     */
    static double getTime();

private:
    /**
     * Synchronize all ranks before timing
     */
    static void synchronize(MPI_Comm comm);
};

#endif // MPI_PERFORMANCE_H

