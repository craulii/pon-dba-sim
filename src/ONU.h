#pragma once
#include <omnetpp.h>
#include <queue>
#include "PONMessages_m.h"

using namespace omnetpp;

namespace pon_dba_sim {

class ONU : public cSimpleModule {
protected:
    void initialize() override;
    void handleMessage(cMessage *msg) override;
    void finish() override;
private:
    int onuId;
    int bufferSize_eMBB, bufferSize_URLLC, bufferSize_mMTC;
    double dataRate;
    simtime_t guardTime;
    simtime_t urllcDeadline;
    double embbRate, urllcRate, mmtcRate;

    cMessage *embbGenMsg, *urllcGenMsg, *mmtcGenMsg, *txDoneMsg;

    std::queue<DataPacket*> embbQueue, urllcQueue, mmtcQueue;

    int remainingGrant_eMBB, remainingGrant_URLLC, remainingGrant_mMTC;
    simtime_t grantStartTime;
    bool transmitting;

    cOutVector latencyVec_eMBB, latencyVec_URLLC, latencyVec_mMTC;
    cOutVector jitterVec_eMBB,  jitterVec_URLLC,  jitterVec_mMTC;

    long pktsGenerated_eMBB, pktsGenerated_URLLC, pktsGenerated_mMTC;
    long pktsDropped_eMBB,   pktsDropped_URLLC,   pktsDropped_mMTC;
    long bytesTransmitted_eMBB, bytesTransmitted_URLLC, bytesTransmitted_mMTC;

    simtime_t lastLatency_eMBB, lastLatency_URLLC, lastLatency_mMTC;

    void generateEMBBPacket();
    void generateURLLCPacket();
    void generateMMTCPacket();
    void processGrant(GrantMessage *grant);
    void transmitNextPacket();
    void sendReport();
    void dropExpiredURLLC();
    void updateDisplayString();

    simtime_t embbInterArrival();
    simtime_t urllcInterArrival();
    simtime_t mmtcInterArrival();
};

} // namespace pon_dba_sim
