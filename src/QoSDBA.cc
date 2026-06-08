#include "QoSDBA.h"
#include <algorithm>

QoSDBA::QoSDBA(double wfqWeightEMBB, double wfqWeightMMTC)
    : weightEMBB(wfqWeightEMBB), weightMMTC(wfqWeightMMTC)
{}

std::vector<ONUGrant> QoSDBA::computeGrants(
    const std::vector<ONUReport>& reports,
    simtime_t cycleStart,
    int maxGrantSizeBytes,
    double guardTimeSec,
    double dataRateBps)
{
    std::vector<ONUGrant> grants;
    simtime_t currentTime = cycleStart;

    for (const auto& rep : reports) {
        int grantEMBB = 0, grantURLLC = 0, grantMMTC = 0;
        int remaining = maxGrantSizeBytes;

        // Paso 1: URLLC con prioridad estricta
        grantURLLC = std::min(rep.queueSize_URLLC, remaining);
        remaining -= grantURLLC;

        // Paso 2: WFQ entre eMBB y mMTC
        if (remaining > 0 && (rep.queueSize_eMBB + rep.queueSize_mMTC) > 0) {
            double totalW = weightEMBB + weightMMTC;
            int idealEMBB = (int)(remaining * weightEMBB / totalW);
            int idealMMTC = remaining - idealEMBB;

            grantEMBB = std::min(rep.queueSize_eMBB, idealEMBB);
            grantMMTC = std::min(rep.queueSize_mMTC, idealMMTC);

            // Ceder sobrante si alguna clase tiene poca demanda
            int sobrante = idealEMBB - grantEMBB;
            if (sobrante > 0)
                grantMMTC = std::min(rep.queueSize_mMTC, grantMMTC + sobrante);

            sobrante = idealMMTC - grantMMTC;
            if (sobrante > 0)
                grantEMBB = std::min(rep.queueSize_eMBB, grantEMBB + sobrante);
        }

        if (grantEMBB + grantURLLC + grantMMTC == 0)
            grantMMTC = 64; // grant mínimo

        int totalGranted = grantEMBB + grantURLLC + grantMMTC;

        ONUGrant g;
        g.onuId           = rep.onuId;
        g.startTime       = currentTime;
        g.grantSize_eMBB  = grantEMBB;
        g.grantSize_URLLC = grantURLLC;
        g.grantSize_mMTC  = grantMMTC;
        grants.push_back(g);

        double slotDuration = (double)totalGranted * 8.0 / dataRateBps;
        currentTime += slotDuration + guardTimeSec;
    }

    return grants;
}
