#pragma once
#include "DBAAlgorithm.h"

// QoS-DBA: Priority-based DBA con WFQ para eMBB/mMTC
class QoSDBA : public DBAAlgorithm {
public:
    explicit QoSDBA(double wfqWeightEMBB = 0.7, double wfqWeightMMTC = 0.3);
    std::vector<ONUGrant> computeGrants(
        const std::vector<ONUReport>& reports,
        simtime_t cycleStart,
        int maxGrantSizeBytes,
        double guardTimeSec,
        double dataRateBps) override;
private:
    double weightEMBB;
    double weightMMTC;
};
