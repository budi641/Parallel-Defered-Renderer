/**
 * MPI Performance Test Program
 * 
 * Demonstrates latency, bandwidth, strong scaling, and weak scaling measurements
 * 
 * Usage:
 *   mpirun -np 4 mpi_performance_test
 */

#ifdef HAVE_MPI
#include <mpi.h>
#endif
#include "mpi_performance.h"
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

// Example work function for scaling tests
double exampleWorkFunction(int problemSize) {
    // Simulate computational work (e.g., matrix multiplication, rendering)
    double sum = 0.0;
    for (int i = 0; i < problemSize; ++i) {
        for (int j = 0; j < problemSize; ++j) {
            sum += std::sin(i * 0.1) * std::cos(j * 0.1);
        }
    }
    return sum; // Return value not used, just for computation
}

int main(int argc, char** argv) {
#ifdef HAVE_MPI
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (rank == 0) {
        std::cout << "=== MPI Performance Measurement Test ===" << std::endl;
        std::cout << "Number of ranks: " << size << std::endl;
        std::cout << std::endl;
    }

    // ============================================
    // A. Latency & Bandwidth Measurements
    // ============================================

    if (rank == 0) {
        std::cout << "Running latency and bandwidth tests..." << std::endl;
    }

    // Latency: small messages (1 byte to 1 KB)
    std::vector<int> latencySizes;
    for (int i = 0; i <= 10; ++i) {
        latencySizes.push_back(1 << i); // 1, 2, 4, 8, ..., 1024 bytes
    }

    std::vector<MPIPerformance::LatencyResult> latencyResults;
    if (size >= 2) {
        latencyResults = MPIPerformance::measureLatency(MPI_COMM_WORLD, latencySizes, 1000);
        if (rank == 0) {
            MPIPerformance::printLatencyResults(latencyResults);
        }
    } else {
        if (rank == 0) {
            std::cout << "Skipping latency test (need at least 2 ranks)" << std::endl;
        }
    }

    // Bandwidth: large messages (1 KB to 10 MB)
    std::vector<int> bandwidthSizes;
    bandwidthSizes.push_back(1024);           // 1 KB
    bandwidthSizes.push_back(1024 * 10);      // 10 KB
    bandwidthSizes.push_back(1024 * 100);     // 100 KB
    bandwidthSizes.push_back(1024 * 1024);   // 1 MB
    bandwidthSizes.push_back(1024 * 1024 * 5); // 5 MB
    bandwidthSizes.push_back(1024 * 1024 * 10); // 10 MB

    std::vector<MPIPerformance::BandwidthResult> bandwidthResults;
    if (size >= 2) {
        bandwidthResults = MPIPerformance::measureBandwidth(MPI_COMM_WORLD, bandwidthSizes, 100);
        if (rank == 0) {
            MPIPerformance::printBandwidthResults(bandwidthResults);
        }
    } else {
        if (rank == 0) {
            std::cout << "Skipping bandwidth test (need at least 2 ranks)" << std::endl;
        }
    }

    // ============================================
    // B. Strong Scaling
    // ============================================

    if (rank == 0) {
        std::cout << "\nRunning strong scaling test..." << std::endl;
        std::cout << "Problem size: 1000x1000 (fixed)" << std::endl;
    }

    std::vector<int> processorCounts;
    for (int i = 1; i <= size; i *= 2) {
        processorCounts.push_back(i);
    }
    if (processorCounts.back() != size) {
        processorCounts.push_back(size);
    }

    std::vector<MPIPerformance::ScalingResult> strongScalingResults;
    if (size >= 1) {
        strongScalingResults = MPIPerformance::measureStrongScaling(
            MPI_COMM_WORLD,
            exampleWorkFunction,
            1000,  // Fixed problem size
            processorCounts
        );
        if (rank == 0) {
            MPIPerformance::printScalingResults(strongScalingResults);
        }
    }

    // ============================================
    // C. Weak Scaling
    // ============================================

    if (rank == 0) {
        std::cout << "\nRunning weak scaling test..." << std::endl;
        std::cout << "Problem size per processor: 500x500" << std::endl;
    }

    std::vector<MPIPerformance::ScalingResult> weakScalingResults;
    if (size >= 1) {
        weakScalingResults = MPIPerformance::measureWeakScaling(
            MPI_COMM_WORLD,
            exampleWorkFunction,
            500,  // Base problem size per processor
            processorCounts
        );
        if (rank == 0) {
            MPIPerformance::printScalingResults(weakScalingResults);
        }
    }

    // ============================================
    // Export Results to CSV
    // ============================================

    if (rank == 0) {
        MPIPerformance::exportToCSV(
            "mpi_performance_results.csv",
            latencyResults,
            bandwidthResults,
            strongScalingResults,
            weakScalingResults
        );
        std::cout << "\n=== Performance Measurement Complete ===" << std::endl;
    }

    MPI_Finalize();
#else
    std::cout << "MPI not available. This program requires MPI." << std::endl;
    return 1;
#endif

    return 0;
}

