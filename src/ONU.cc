#include "ONU.h"
#include <cstdio>
#include <algorithm>

namespace pon_dba_sim {

Define_Module(ONU);

void ONU::initialize()
{
    onuId            = par("onuId");
    bufferSize_eMBB  = par("bufferSize_eMBB").intValue();
    bufferSize_URLLC = par("bufferSize_URLLC").intValue();
    bufferSize_mMTC  = par("bufferSize_mMTC").intValue();
    dataRate         = par("dataRate");
    guardTime        = par("guardTime");
    urllcDeadline    = par("urllcDeadline");
    embbRate         = par("embbRate");
    urllcRate        = par("urllcRate");
    mmtcRate         = par("mmtcRate");

    remainingGrant_eMBB = remainingGrant_URLLC = remainingGrant_mMTC = 0;
    transmitting = false;

    pktsGenerated_eMBB  = pktsGenerated_URLLC  = pktsGenerated_mMTC  = 0;
    pktsDropped_eMBB    = pktsDropped_URLLC    = pktsDropped_mMTC    = 0;
    bytesTransmitted_eMBB = bytesTransmitted_URLLC = bytesTransmitted_mMTC = 0;
    lastLatency_eMBB = lastLatency_URLLC = lastLatency_mMTC = -1;

    char name[64];
    snprintf(name, sizeof(name), "latency_eMBB_onu%d", onuId);  latencyVec_eMBB.setName(name);
    snprintf(name, sizeof(name), "latency_URLLC_onu%d", onuId); latencyVec_URLLC.setName(name);
    snprintf(name, sizeof(name), "latency_mMTC_onu%d", onuId);  latencyVec_mMTC.setName(name);
    snprintf(name, sizeof(name), "jitter_eMBB_onu%d", onuId);   jitterVec_eMBB.setName(name);
    snprintf(name, sizeof(name), "jitter_URLLC_onu%d", onuId);  jitterVec_URLLC.setName(name);
    snprintf(name, sizeof(name), "jitter_mMTC_onu%d", onuId);   jitterVec_mMTC.setName(name);

    embbGenMsg  = new cMessage("genEMBB");
    urllcGenMsg = new cMessage("genURLLC");
    mmtcGenMsg  = new cMessage("genMMTC");
    txDoneMsg   = new cMessage("txDone");

    double offset = onuId * 0.0001;
    scheduleAt(simTime() + offset + embbInterArrival(),  embbGenMsg);
    scheduleAt(simTime() + offset + urllcInterArrival(), urllcGenMsg);
    scheduleAt(simTime() + offset + mmtcInterArrival(),  mmtcGenMsg);

    EV << "ONU " << onuId << " inicializada\n";
}

simtime_t ONU::embbInterArrival()
{
    // Pareto(alpha=1.5): E[X] = xm * alpha/(alpha-1) = 3*xm
    // Para que E[X] = (1250*8)/embbRate (media deseada), xm = media/3
    double xm = (1250.0 * 8.0) / embbRate / 3.0;
    double u = uniform(0.001, 0.999);
    return xm * pow(u, -1.0 / 1.5);
}

simtime_t ONU::urllcInterArrival()
{
    return exponential((128.0 * 8.0) / urllcRate);
}

simtime_t ONU::mmtcInterArrival()
{
    return ((100.0 * 8.0) / mmtcRate) * uniform(0.8, 1.2);
}

void ONU::generateEMBBPacket()
{
    pktsGenerated_eMBB++;
    int pktSize = (int)uniform(1000, 1500);

    int currentBytes = 0;
    std::queue<DataPacket*> tmp = embbQueue;
    while (!tmp.empty()) { currentBytes += tmp.front()->getDataSize(); tmp.pop(); }

    if (currentBytes + pktSize > bufferSize_eMBB) {
        pktsDropped_eMBB++;
        if (hasGUI()) { bubble("DROP eMBB!"); getDisplayString().setTagArg("i2", 0, "status/excl"); }
        return;
    }
    DataPacket *pkt = new DataPacket("eMBB-data");
    pkt->setSourceONU(onuId);
    pkt->setTrafficClass(0);
    pkt->setCreationTime(simTime());
    pkt->setDeadline(-1);
    pkt->setDataSize(pktSize);
    pkt->setByteLength(pktSize);
    embbQueue.push(pkt);
}

void ONU::generateURLLCPacket()
{
    pktsGenerated_URLLC++;
    int pktSize = (int)uniform(32, 256);

    int currentBytes = 0;
    std::queue<DataPacket*> tmp = urllcQueue;
    while (!tmp.empty()) { currentBytes += tmp.front()->getDataSize(); tmp.pop(); }

    if (currentBytes + pktSize > bufferSize_URLLC) {
        pktsDropped_URLLC++;
        if (hasGUI()) bubble("DROP URLLC!");
        return;
    }
    DataPacket *pkt = new DataPacket("URLLC-data");
    pkt->setSourceONU(onuId);
    pkt->setTrafficClass(1);
    pkt->setCreationTime(simTime());
    pkt->setDeadline(simTime() + urllcDeadline);
    pkt->setDataSize(pktSize);
    pkt->setByteLength(pktSize);
    urllcQueue.push(pkt);
}

void ONU::generateMMTCPacket()
{
    pktsGenerated_mMTC++;
    int pktSize = (int)uniform(20, 200);

    int currentBytes = 0;
    std::queue<DataPacket*> tmp = mmtcQueue;
    while (!tmp.empty()) { currentBytes += tmp.front()->getDataSize(); tmp.pop(); }

    if (currentBytes + pktSize > bufferSize_mMTC) {
        pktsDropped_mMTC++;
        if (hasGUI()) bubble("DROP mMTC!");
        return;
    }
    DataPacket *pkt = new DataPacket("mMTC-data");
    pkt->setSourceONU(onuId);
    pkt->setTrafficClass(2);
    pkt->setCreationTime(simTime());
    pkt->setDeadline(-1);
    pkt->setDataSize(pktSize);
    pkt->setByteLength(pktSize);
    mmtcQueue.push(pkt);
}

void ONU::processGrant(GrantMessage *grant)
{
    remainingGrant_eMBB  = grant->getGrantSize_eMBB();
    remainingGrant_URLLC = grant->getGrantSize_URLLC();
    remainingGrant_mMTC  = grant->getGrantSize_mMTC();
    grantStartTime       = grant->getStartTime();
    delete grant;
    if (!transmitting) transmitNextPacket();
}

void ONU::dropExpiredURLLC()
{
    simtime_t now = simTime();
    while (!urllcQueue.empty()) {
        DataPacket *pkt = urllcQueue.front();
        simtime_t dl = pkt->getDeadline();
        if (dl > 0 && now > dl) {
            pktsDropped_URLLC++;
            if (hasGUI()) bubble("URLLC expired!");
            delete pkt; urllcQueue.pop();
        } else break;
    }
}

void ONU::transmitNextPacket()
{
    dropExpiredURLLC();

    DataPacket *pkt    = nullptr;
    int *remaining     = nullptr;
    cOutVector *latVec = nullptr;
    cOutVector *jitVec = nullptr;
    simtime_t *lastLat = nullptr;
    long *bytesTx      = nullptr;

    if (!urllcQueue.empty() && remainingGrant_URLLC > 0) {
        pkt = urllcQueue.front(); urllcQueue.pop();
        remaining = &remainingGrant_URLLC; latVec = &latencyVec_URLLC; jitVec = &jitterVec_URLLC;
        lastLat = &lastLatency_URLLC; bytesTx = &bytesTransmitted_URLLC;
    } else if (!embbQueue.empty() && remainingGrant_eMBB > 0) {
        pkt = embbQueue.front(); embbQueue.pop();
        remaining = &remainingGrant_eMBB; latVec = &latencyVec_eMBB; jitVec = &jitterVec_eMBB;
        lastLat = &lastLatency_eMBB; bytesTx = &bytesTransmitted_eMBB;
    } else if (!mmtcQueue.empty() && remainingGrant_mMTC > 0) {
        pkt = mmtcQueue.front(); mmtcQueue.pop();
        remaining = &remainingGrant_mMTC; latVec = &latencyVec_mMTC; jitVec = &jitterVec_mMTC;
        lastLat = &lastLatency_mMTC; bytesTx = &bytesTransmitted_mMTC;
    }

    if (!pkt) { transmitting = false; updateDisplayString(); return; }

    transmitting = true;
    int sz = pkt->getDataSize();
    *remaining -= sz; if (*remaining < 0) *remaining = 0;
    *bytesTx += sz;

    simtime_t latency = simTime() - pkt->getCreationTime();
    latVec->record(latency.dbl() * 1e6);

    if (*lastLat >= 0) {
        simtime_t jitter = fabs(latency - *lastLat);
        jitVec->record(jitter.dbl() * 1e6);
    }
    *lastLat = latency;

    if (pkt->getTrafficClass() == 1) {
        simtime_t dl = pkt->getDeadline();
        if (dl > 0 && simTime() > dl) {
            pktsDropped_URLLC++;
            if (hasGUI()) bubble("URLLC missed deadline!");
        } else {
            if (hasGUI()) bubble("URLLC OK");
        }
    }

    double txTime = (double)sz * 8.0 / dataRate;
    send(pkt, "ponPort$o");
    scheduleAt(simTime() + txTime, txDoneMsg);
}

void ONU::sendReport()
{
    int b0 = 0, b1 = 0, b2 = 0;
    std::queue<DataPacket*> tmp;
    tmp = embbQueue;  while (!tmp.empty()) { b0 += tmp.front()->getDataSize(); tmp.pop(); }
    tmp = urllcQueue; while (!tmp.empty()) { b1 += tmp.front()->getDataSize(); tmp.pop(); }
    tmp = mmtcQueue;  while (!tmp.empty()) { b2 += tmp.front()->getDataSize(); tmp.pop(); }

    ReportMessage *report = new ReportMessage("REPORT");
    report->setSourceONU(onuId);
    report->setQueueSize_eMBB(b0);
    report->setQueueSize_URLLC(b1);
    report->setQueueSize_mMTC(b2);
    send(report, "ponPort$o");
}

void ONU::updateDisplayString()
{
    if (!hasGUI()) return;
    int b0 = 0, b1 = 0, b2 = 0;
    std::queue<DataPacket*> tmp;
    tmp = embbQueue;  while (!tmp.empty()) { b0 += tmp.front()->getDataSize(); tmp.pop(); }
    tmp = urllcQueue; while (!tmp.empty()) { b1 += tmp.front()->getDataSize(); tmp.pop(); }
    tmp = mmtcQueue;  while (!tmp.empty()) { b2 += tmp.front()->getDataSize(); tmp.pop(); }
    char buf[80];
    snprintf(buf, sizeof(buf), "Q:%d/%d/%dB", b0, b1, b2);
    getDisplayString().setTagArg("t", 0, buf);
}

void ONU::handleMessage(cMessage *msg)
{
    if (msg == embbGenMsg) {
        generateEMBBPacket();
        scheduleAt(simTime() + embbInterArrival(), embbGenMsg);
    } else if (msg == urllcGenMsg) {
        generateURLLCPacket();
        scheduleAt(simTime() + urllcInterArrival(), urllcGenMsg);
    } else if (msg == mmtcGenMsg) {
        generateMMTCPacket();
        scheduleAt(simTime() + mmtcInterArrival(), mmtcGenMsg);
    } else if (msg == txDoneMsg) {
        transmitting = false;
        transmitNextPacket();
    } else if (auto *grant = dynamic_cast<GrantMessage*>(msg)) {
        int total = grant->getGrantSize_eMBB() + grant->getGrantSize_URLLC() + grant->getGrantSize_mMTC();
        if (total > 0) {
            processGrant(grant);
        } else {
            delete grant;
            sendReport();
        }
    } else {
        EV_WARN << "ONU " << onuId << ": mensaje desconocido " << msg->getName() << "\n";
        delete msg;
    }
}

void ONU::finish()
{
    char name[64];
    auto scl = [&](const char *fmt, long val) {
        snprintf(name, sizeof(name), fmt, onuId);
        recordScalar(name, val);
    };
    auto scd = [&](const char *fmt, double val) {
        snprintf(name, sizeof(name), fmt, onuId);
        recordScalar(name, val);
    };

    scl("pktsGenerated_eMBB_onu%d",  pktsGenerated_eMBB);
    scl("pktsGenerated_URLLC_onu%d", pktsGenerated_URLLC);
    scl("pktsGenerated_mMTC_onu%d",  pktsGenerated_mMTC);
    scl("pktsDropped_eMBB_onu%d",    pktsDropped_eMBB);
    scl("pktsDropped_URLLC_onu%d",   pktsDropped_URLLC);
    scl("pktsDropped_mMTC_onu%d",    pktsDropped_mMTC);
    scl("bytesTransmitted_eMBB_onu%d",  bytesTransmitted_eMBB);
    scl("bytesTransmitted_URLLC_onu%d", bytesTransmitted_URLLC);
    scl("bytesTransmitted_mMTC_onu%d",  bytesTransmitted_mMTC);

    if (pktsGenerated_eMBB  > 0) scd("lossRate_eMBB_onu%d",  (double)pktsDropped_eMBB  / pktsGenerated_eMBB);
    if (pktsGenerated_URLLC > 0) scd("lossRate_URLLC_onu%d", (double)pktsDropped_URLLC / pktsGenerated_URLLC);
    if (pktsGenerated_mMTC  > 0) scd("lossRate_mMTC_onu%d",  (double)pktsDropped_mMTC  / pktsGenerated_mMTC);

    // Cancelar y liberar todos los self-messages pendientes
    cancelAndDelete(embbGenMsg);  embbGenMsg  = nullptr;
    cancelAndDelete(urllcGenMsg); urllcGenMsg = nullptr;
    cancelAndDelete(mmtcGenMsg);  mmtcGenMsg  = nullptr;
    cancelAndDelete(txDoneMsg);   txDoneMsg   = nullptr;

    while (!embbQueue.empty())  { delete embbQueue.front();  embbQueue.pop(); }
    while (!urllcQueue.empty()) { delete urllcQueue.front(); urllcQueue.pop(); }
    while (!mmtcQueue.empty())  { delete mmtcQueue.front();  mmtcQueue.pop(); }
}

} // namespace pon_dba_sim
