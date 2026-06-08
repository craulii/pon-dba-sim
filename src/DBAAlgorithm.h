#pragma once
#include <vector>
#include <omnetpp.h>

using namespace omnetpp;

// Información de reporte de una ONU
struct ONUReport {
    int onuId;
    int queueSize_eMBB;
    int queueSize_URLLC;
    int queueSize_mMTC;
};

// Grant calculado para una ONU
struct ONUGrant {
    int onuId;
    simtime_t startTime;
    int grantSize_eMBB;
    int grantSize_URLLC;
    int grantSize_mMTC;
};

// Interfaz base para algoritmos DBA
class DBAAlgorithm {
public:
    virtual ~DBAAlgorithm() = default;
    virtual std::vector<ONUGrant> computeGrants(
        const std::vector<ONUReport>& reports,
        simtime_t cycleStart,
        int maxGrantSizeBytes,
        double guardTimeSec,
        double dataRateBps) = 0;
};
