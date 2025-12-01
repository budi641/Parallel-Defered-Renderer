#include "mpi_performance.h"
#include <iostream>
#include <iomanip>
#include <fstream>
#include <algorithm>
#include <numeric>
#include <cmath>

#ifdef _WIN32
#include <windows.h>
#else
#include <sys/time.h>
#include <unistd.h>
#endif

#ifdef HAVE_MPI

double MPIPerformance::getTime()
{
#ifdef _WIN32
    LARGE_INTEGER frequency, counter;
    QueryPerformanceFrequency(&frequency);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)frequency.QuadPart;
#else
    struct timeval tv;
    gettimeofday(&tv, nullptr);
    return tv.tv_sec + tv.tv_usec / 1000000.0;
#endif
}

void MPIPerformance::synchronize(MPI_Comm comm)
{
    MPI_Barrier(comm);
}

std::vector<MPIPerformance::LatencyResult> MPIPerformance::measureLatency(
    MPI_Comm comm,
    const std::vector<int>& messageSizes,
    int iterations)
{
    int rank, size;
    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &size);

    std::vector<LatencyResult> results;

    if (size < 2) {
        std::cerr << "Warning: Need at least 2 ranks for latency measurement" << std::endl;
        return results;
    }

    for (int msgSize : messageSizes) {
        std::vector<char> sendBuffer(msgSize, 0);
        std::vector<char> recvBuffer(msgSize, 0);
        std::vector<double> times;

        // Warm-up
        if (rank == 0) {
            MPI_Send(sendBuffer.data(), msgSize, MPI_BYTE, 1, 0, comm);
            MPI_Recv(recvBuffer.data(), msgSize, MPI_BYTE, 1, 0, comm, MPI_STATUS_IGNORE);
        } else if (rank == 1) {
            MPI_Recv(recvBuffer.data(), msgSize, MPI_BYTE, 0, 0, comm, MPI_STATUS_IGNORE);
            MPI_Send(sendBuffer.data(), msgSize, MPI_BYTE, 0, 0, comm);
        }
        synchronize(comm);

        // Measure round-trip time
        for (int i = 0; i < iterations; ++i) {
            synchronize(comm);
            double start = getTime();

            if (rank == 0) {
                MPI_Send(sendBuffer.data(), msgSize, MPI_BYTE, 1, 0, comm);
                MPI_Recv(recvBuffer.data(), msgSize, MPI_BYTE, 1, 0, comm, MPI_STATUS_IGNORE);
            } else if (rank == 1) {
                MPI_Recv(recvBuffer.data(), msgSize, MPI_BYTE, 0, 0, comm, MPI_STATUS_IGNORE);
                MPI_Send(sendBuffer.data(), msgSize, MPI_BYTE, 0, 0, comm);
            }

            double end = getTime();
            double roundTrip = (end - start) * 1000000.0; // Convert to microseconds
            times.push_back(roundTrip);
        }

        // Calculate statistics (only on rank 0)
        if (rank == 0) {
            // Remove outliers (top and bottom 10%)
            std::sort(times.begin(), times.end());
            int removeCount = times.size() / 10;
            times.erase(times.begin(), times.begin() + removeCount);
            times.erase(times.end() - removeCount, times.end());

            double avgRoundTrip = std::accumulate(times.begin(), times.end(), 0.0) / times.size();
            double latency = avgRoundTrip / 2.0; // One-way latency

            LatencyResult result;
            result.messageSize = msgSize;
            result.latency = latency;
            result.roundTripTime = avgRoundTrip;
            results.push_back(result);
        }
    }

    return results;
}

std::vector<MPIPerformance::BandwidthResult> MPIPerformance::measureBandwidth(
    MPI_Comm comm,
    const std::vector<int>& messageSizes,
    int iterations)
{
    int rank, size;
    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &size);

    std::vector<BandwidthResult> results;

    if (size < 2) {
        std::cerr << "Warning: Need at least 2 ranks for bandwidth measurement" << std::endl;
        return results;
    }

    for (int msgSize : messageSizes) {
        std::vector<char> sendBuffer(msgSize, 0);
        std::vector<char> recvBuffer(msgSize, 0);
        std::vector<double> times;

        // Warm-up
        if (rank == 0) {
            MPI_Send(sendBuffer.data(), msgSize, MPI_BYTE, 1, 0, comm);
        } else if (rank == 1) {
            MPI_Recv(recvBuffer.data(), msgSize, MPI_BYTE, 0, 0, comm, MPI_STATUS_IGNORE);
        }
        synchronize(comm);

        // Measure one-way transfer time
        for (int i = 0; i < iterations; ++i) {
            synchronize(comm);
            double start = getTime();

            if (rank == 0) {
                MPI_Send(sendBuffer.data(), msgSize, MPI_BYTE, 1, 0, comm);
            } else if (rank == 1) {
                MPI_Recv(recvBuffer.data(), msgSize, MPI_BYTE, 0, 0, comm, MPI_STATUS_IGNORE);
            }

            double end = getTime();
            double transferTime = (end - start) * 1000000.0; // Convert to microseconds
            times.push_back(transferTime);
        }

        // Calculate statistics (only on rank 1)
        if (rank == 1) {
            // Remove outliers (top and bottom 10%)
            std::sort(times.begin(), times.end());
            int removeCount = times.size() / 10;
            times.erase(times.begin(), times.begin() + removeCount);
            times.erase(times.end() - removeCount, times.end());

            double avgTime = std::accumulate(times.begin(), times.end(), 0.0) / times.size();
            double bandwidth = (msgSize / (1024.0 * 1024.0)) / (avgTime / 1000000.0); // MB/s

            BandwidthResult result;
            result.messageSize = msgSize;
            result.bandwidth = bandwidth;
            result.transferTime = avgTime;
            results.push_back(result);
        }
    }

    // Gather results to rank 0
    if (rank == 1 && results.size() > 0) {
        // Send all results to rank 0
        int count = results.size();
        MPI_Send(&count, 1, MPI_INT, 0, 0, comm);
        for (const auto& result : results) {
            MPI_Send(const_cast<BandwidthResult*>(&result), sizeof(BandwidthResult), MPI_BYTE, 0, 0, comm);
        }
    } else if (rank == 0) {
        // Receive results from rank 1
        int count = 0;
        MPI_Recv(&count, 1, MPI_INT, 1, 0, comm, MPI_STATUS_IGNORE);
        results.resize(count);
        for (int i = 0; i < count; ++i) {
            MPI_Recv(&results[i], sizeof(BandwidthResult), MPI_BYTE, 1, 0, comm, MPI_STATUS_IGNORE);
        }
    }

    return results;
}

std::vector<MPIPerformance::ScalingResult> MPIPerformance::measureStrongScaling(
    MPI_Comm comm,
    std::function<double(int)> workFunction,
    int problemSize,
    const std::vector<int>& processorCounts)
{
    int rank, size;
    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &size);

    std::vector<ScalingResult> results;
    double baselineTime = 0.0;

    for (int numProcs : processorCounts) {
        if (numProcs > size) {
            continue; // Skip if we don't have enough ranks
        }

        // Create sub-communicator with numProcs ranks
        MPI_Comm subComm;
        int color = (rank < numProcs) ? 0 : MPI_UNDEFINED;
        MPI_Comm_split(comm, color, rank, &subComm);

        if (subComm != MPI_COMM_NULL) {
            synchronize(subComm);
            double start = getTime();
            
            // Perform work
            double execTime = workFunction(problemSize);
            
            double end = getTime();
            double totalTime = end - start;

            // Gather execution time to rank 0 of sub-communicator
            int subRank;
            MPI_Comm_rank(subComm, &subRank);
            
            double maxTime = totalTime;
            MPI_Reduce(&totalTime, &maxTime, 1, MPI_DOUBLE, MPI_MAX, 0, subComm);

            if (subRank == 0) {
                ScalingResult result;
                result.numRanks = numProcs;
                result.executionTime = maxTime;
                
                if (baselineTime == 0.0) {
                    baselineTime = maxTime;
                    result.speedup = 1.0;
                } else {
                    result.speedup = baselineTime / maxTime;
                }
                result.efficiency = result.speedup / numProcs;
                
                results.push_back(result);
            }

            MPI_Comm_free(&subComm);
        }

        synchronize(comm);
    }

    // Gather all results to rank 0
    if (rank == 0) {
        // Results are already collected
    }

    return results;
}

std::vector<MPIPerformance::ScalingResult> MPIPerformance::measureWeakScaling(
    MPI_Comm comm,
    std::function<double(int)> workFunction,
    int baseProblemSize,
    const std::vector<int>& processorCounts)
{
    int rank, size;
    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &size);

    std::vector<ScalingResult> results;
    double baselineTime = 0.0;

    for (int numProcs : processorCounts) {
        if (numProcs > size) {
            continue; // Skip if we don't have enough ranks
        }

        // Create sub-communicator with numProcs ranks
        MPI_Comm subComm;
        int color = (rank < numProcs) ? 0 : MPI_UNDEFINED;
        MPI_Comm_split(comm, color, rank, &subComm);

        if (subComm != MPI_COMM_NULL) {
            // Problem size scales with number of processors
            int scaledProblemSize = baseProblemSize * numProcs;
            
            synchronize(subComm);
            double start = getTime();
            
            // Perform work
            double execTime = workFunction(scaledProblemSize);
            
            double end = getTime();
            double totalTime = end - start;

            // Gather execution time to rank 0 of sub-communicator
            int subRank;
            MPI_Comm_rank(subComm, &subRank);
            
            double maxTime = totalTime;
            MPI_Reduce(&totalTime, &maxTime, 1, MPI_DOUBLE, MPI_MAX, 0, subComm);

            if (subRank == 0) {
                ScalingResult result;
                result.numRanks = numProcs;
                result.executionTime = maxTime;
                
                if (baselineTime == 0.0) {
                    baselineTime = maxTime;
                    result.speedup = 1.0;
                } else {
                    // For weak scaling, ideal speedup is 1.0 (constant time)
                    result.speedup = baselineTime / maxTime;
                }
                result.efficiency = result.speedup; // Efficiency = speedup for weak scaling
                
                results.push_back(result);
            }

            MPI_Comm_free(&subComm);
        }

        synchronize(comm);
    }

    return results;
}

void MPIPerformance::printLatencyResults(const std::vector<LatencyResult>& results)
{
    std::cout << "\n=== Latency Measurement Results ===" << std::endl;
    std::cout << std::left << std::setw(15) << "Message Size"
              << std::setw(20) << "Latency (μs)"
              << std::setw(20) << "Round-Trip (μs)" << std::endl;
    std::cout << std::string(55, '-') << std::endl;

    for (const auto& result : results) {
        std::cout << std::left << std::setw(15) << result.messageSize
                  << std::setw(20) << std::fixed << std::setprecision(2) << result.latency
                  << std::setw(20) << result.roundTripTime << std::endl;
    }
}

void MPIPerformance::printBandwidthResults(const std::vector<BandwidthResult>& results)
{
    std::cout << "\n=== Bandwidth Measurement Results ===" << std::endl;
    std::cout << std::left << std::setw(15) << "Message Size"
              << std::setw(20) << "Bandwidth (MB/s)"
              << std::setw(20) << "Transfer Time (μs)" << std::endl;
    std::cout << std::string(55, '-') << std::endl;

    for (const auto& result : results) {
        std::cout << std::left << std::setw(15) << result.messageSize
                  << std::setw(20) << std::fixed << std::setprecision(2) << result.bandwidth
                  << std::setw(20) << result.transferTime << std::endl;
    }
}

void MPIPerformance::printScalingResults(const std::vector<ScalingResult>& results)
{
    std::cout << "\n=== Scaling Results ===" << std::endl;
    std::cout << std::left << std::setw(12) << "Processors"
              << std::setw(18) << "Time (s)"
              << std::setw(15) << "Speedup"
              << std::setw(15) << "Efficiency" << std::endl;
    std::cout << std::string(60, '-') << std::endl;

    for (const auto& result : results) {
        std::cout << std::left << std::setw(12) << result.numRanks
                  << std::setw(18) << std::fixed << std::setprecision(6) << result.executionTime
                  << std::setw(15) << std::setprecision(2) << result.speedup
                  << std::setw(15) << std::setprecision(2) << result.efficiency << std::endl;
    }
}

void MPIPerformance::exportToCSV(
    const std::string& filename,
    const std::vector<LatencyResult>& latencyResults,
    const std::vector<BandwidthResult>& bandwidthResults,
    const std::vector<ScalingResult>& strongScalingResults,
    const std::vector<ScalingResult>& weakScalingResults)
{
    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Error: Could not open file " << filename << std::endl;
        return;
    }

    // Latency results
    file << "Latency Results\n";
    file << "Message Size (bytes),Latency (us),Round-Trip Time (us)\n";
    for (const auto& result : latencyResults) {
        file << result.messageSize << ","
             << result.latency << ","
             << result.roundTripTime << "\n";
    }
    file << "\n";

    // Bandwidth results
    file << "Bandwidth Results\n";
    file << "Message Size (bytes),Bandwidth (MB/s),Transfer Time (us)\n";
    for (const auto& result : bandwidthResults) {
        file << result.messageSize << ","
             << result.bandwidth << ","
             << result.transferTime << "\n";
    }
    file << "\n";

    // Strong scaling results
    file << "Strong Scaling Results\n";
    file << "Processors,Execution Time (s),Speedup,Efficiency\n";
    for (const auto& result : strongScalingResults) {
        file << result.numRanks << ","
             << result.executionTime << ","
             << result.speedup << ","
             << result.efficiency << "\n";
    }
    file << "\n";

    // Weak scaling results
    file << "Weak Scaling Results\n";
    file << "Processors,Execution Time (s),Speedup,Efficiency\n";
    for (const auto& result : weakScalingResults) {
        file << result.numRanks << ","
             << result.executionTime << ","
             << result.speedup << ","
             << result.efficiency << "\n";
    }

    file.close();
    std::cout << "Results exported to " << filename << std::endl;
}

#else // HAVE_MPI not defined

// Dummy implementations when MPI is not available
double MPIPerformance::getTime() { return 0.0; }
void MPIPerformance::synchronize(MPI_Comm) {}
std::vector<MPIPerformance::LatencyResult> MPIPerformance::measureLatency(MPI_Comm, const std::vector<int>&, int) { return {}; }
std::vector<MPIPerformance::BandwidthResult> MPIPerformance::measureBandwidth(MPI_Comm, const std::vector<int>&, int) { return {}; }
std::vector<MPIPerformance::ScalingResult> MPIPerformance::measureStrongScaling(MPI_Comm, std::function<double(int)>, int, const std::vector<int>&) { return {}; }
std::vector<MPIPerformance::ScalingResult> MPIPerformance::measureWeakScaling(MPI_Comm, std::function<double(int)>, int, const std::vector<int>&) { return {}; }
void MPIPerformance::printLatencyResults(const std::vector<LatencyResult>&) {}
void MPIPerformance::printBandwidthResults(const std::vector<BandwidthResult>&) {}
void MPIPerformance::printScalingResults(const std::vector<ScalingResult>&) {}
void MPIPerformance::exportToCSV(const std::string&, const std::vector<LatencyResult>&, const std::vector<BandwidthResult>&, const std::vector<ScalingResult>&, const std::vector<ScalingResult>&) {}

#endif // HAVE_MPI

