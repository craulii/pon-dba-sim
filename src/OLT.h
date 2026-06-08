#pragma once
#include <omnetpp.h>
#include <vector>
#include <memory>
#include "DBAAlgorithm.h"
#include "PONMessages_m.h"

using namespace omnetpp;

namespace pon_dba_sim {

class OLT : public cSimpleModule {
protected:
    void initialize() override;
    void handleMessage(cMessage *msg) override;
    void finish() override;
private:
    std::string dbaAlgorithm;
    int numONUs;
    int maxGrantSize;
    simtime_t pollingCycleTime;
    simtime_t guardTime;
    double dataRate;

    std::unique_ptr<DBAAlgorithm> dba;

    std::vector<ONUReport> pendingReports;
    int reportsReceived;
    simtime_t cycleStartTime;

    cMessage *startCycleMsg;
    cOutVector cycleTimeVec;
    long totalCycles;

    void startNewCycle();
    void processReport(ReportMessage *report);
    void computeAndSendGrants();
    void sendGrant(const ONUGrant& grant);
};

} // namespace pon_dba_sim
