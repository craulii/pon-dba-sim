#include "OLT.h"
#include "IPACT.h"
#include "QoSDBA.h"

namespace pon_dba_sim {

Define_Module(OLT);

void OLT::initialize()
{
    dbaAlgorithm     = par("dbaAlgorithm").stdstringValue();
    numONUs          = par("numONUs");
    maxGrantSize     = par("maxGrantSize").intValue();
    pollingCycleTime = par("pollingCycleTime");
    guardTime        = par("guardTime");
    dataRate         = par("dataRate");

    if (dbaAlgorithm == "IPACT") {
        dba = std::make_unique<IPACT>();
    } else if (dbaAlgorithm == "QoSDBA") {
        double wE = par("wfqWeightEMBB");
        double wM = par("wfqWeightMMTC");
        dba = std::make_unique<QoSDBA>(wE, wM);
    } else {
        throw cRuntimeError("Algoritmo DBA desconocido: %s", dbaAlgorithm.c_str());
    }

    reportsReceived = 0;
    totalCycles     = 0;
    pendingReports.resize(numONUs);

    cycleTimeVec.setName("cycleTime");
    cycleTimeVec.enable();

    getDisplayString().setTagArg("t", 0, (std::string("DBA: ") + dbaAlgorithm).c_str());

    startCycleMsg = new cMessage("startCycle");
    scheduleAt(simTime(), startCycleMsg);

    EV << "OLT inicializada: " << dbaAlgorithm << ", ONUs=" << numONUs << "\n";
}

void OLT::startNewCycle()
{
    reportsReceived = 0;
    cycleStartTime  = simTime();

    for (int i = 0; i < numONUs; i++) {
        pendingReports[i] = {i, 0, 0, 0};

        GrantMessage *poll = new GrantMessage("POLL");
        poll->setDestONU(i);
        poll->setStartTime(simTime());
        poll->setGrantSize_eMBB(0);
        poll->setGrantSize_URLLC(0);
        poll->setGrantSize_mMTC(0);
        send(poll, "ponPort$o");
    }
}

void OLT::processReport(ReportMessage *report)
{
    int id = report->getSourceONU();
    if (id >= 0 && id < numONUs) {
        pendingReports[id].onuId          = id;
        pendingReports[id].queueSize_eMBB  = report->getQueueSize_eMBB();
        pendingReports[id].queueSize_URLLC = report->getQueueSize_URLLC();
        pendingReports[id].queueSize_mMTC  = report->getQueueSize_mMTC();
        reportsReceived++;
    }
    delete report;

    if (reportsReceived >= numONUs)
        computeAndSendGrants();
}

void OLT::computeAndSendGrants()
{
    simtime_t ct = simTime() - cycleStartTime;
    cycleTimeVec.record(ct.dbl() * 1e3);
    totalCycles++;

    auto grants = dba->computeGrants(
        pendingReports, simTime(), maxGrantSize, guardTime.dbl(), dataRate);

    for (const auto& g : grants)
        sendGrant(g);

    scheduleAt(simTime() + pollingCycleTime, startCycleMsg);
}

void OLT::sendGrant(const ONUGrant& grant)
{
    GrantMessage *grantMsg = new GrantMessage("GRANT");
    grantMsg->setDestONU(grant.onuId);
    grantMsg->setStartTime(grant.startTime);
    grantMsg->setGrantSize_eMBB(grant.grantSize_eMBB);
    grantMsg->setGrantSize_URLLC(grant.grantSize_URLLC);
    grantMsg->setGrantSize_mMTC(grant.grantSize_mMTC);
    send(grantMsg, "ponPort$o");
}

void OLT::handleMessage(cMessage *msg)
{
    if (msg == startCycleMsg) {
        startNewCycle();
    } else if (auto *report = dynamic_cast<ReportMessage*>(msg)) {
        processReport(report);
    } else {
        EV << "OLT: paquete de datos recibido\n";
        delete msg;
    }
}

void OLT::finish()
{
    recordScalar("totalCycles", totalCycles);
    cancelAndDelete(startCycleMsg);
    startCycleMsg = nullptr;
}

} // namespace pon_dba_sim
