#pragma once
#include "DBAAlgorithm.h"

// IPACT: Interleaved Polling with Adaptive Cycle Time
// Referencia: Kramer & Mukherjee (2002)
class IPACT : public DBAAlgorithm {
public:
    std::vector<ONUGrant> computeGrants(
        const std::vector<ONUReport>& reports,
        simtime_t cycleStart,
        int maxGrantSizeBytes,
        double guardTimeSec,
        double dataRateBps) override;
};
