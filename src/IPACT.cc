#include "IPACT.h"
#include <algorithm>

std::vector<ONUGrant> IPACT::computeGrants(
    const std::vector<ONUReport>& reports,
    simtime_t cycleStart,
    int maxGrantSizeBytes,
    double guardTimeSec,
    double dataRateBps)
{
    std::vector<ONUGrant> grants;
    simtime_t currentTime = cycleStart;

    for (const auto& rep : reports) {
        int totalBytes = rep.queueSize_eMBB + rep.queueSize_URLLC + rep.queueSize_mMTC;
        int granted = std::min(totalBytes, maxGrantSizeBytes);

        if (granted == 0) granted = 64; // grant mínimo para mantener polling

        // Distribuir proporcionalmente entre clases (sin QoS)
        int grantEMBB = 0, grantURLLC = 0, grantMMTC = 0;
        if (totalBytes > 0) {
            grantEMBB  = (int)((double)rep.queueSize_eMBB  / totalBytes * granted);
            grantURLLC = (int)((double)rep.queueSize_URLLC / totalBytes * granted);
            grantMMTC  = granted - grantEMBB - grantURLLC;
        } else {
            grantMMTC = granted;
        }

        ONUGrant g;
        g.onuId           = rep.onuId;
        g.startTime       = currentTime;
        g.grantSize_eMBB  = grantEMBB;
        g.grantSize_URLLC = grantURLLC;
        g.grantSize_mMTC  = grantMMTC;
        grants.push_back(g);

        double slotDuration = (double)granted * 8.0 / dataRateBps;
        currentTime += slotDuration + guardTimeSec;
    }

    return grants;
}
