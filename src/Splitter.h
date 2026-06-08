#pragma once
#include <omnetpp.h>
using namespace omnetpp;

namespace pon_dba_sim {

class Splitter : public cSimpleModule {
protected:
    void initialize() override;
    void handleMessage(cMessage *msg) override;
private:
    int numONUs;
};

} // namespace pon_dba_sim
