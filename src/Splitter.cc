#include "Splitter.h"
#include "PONMessages_m.h"

namespace pon_dba_sim {

Define_Module(Splitter);

void Splitter::initialize()
{
    numONUs = par("numONUs");
    EV << "Splitter inicializado con " << numONUs << " ONUs\n";
}

void Splitter::handleMessage(cMessage *msg)
{
    if (msg->arrivedOn("oltPort$i")) {
        GrantMessage *grant = check_and_cast<GrantMessage*>(msg);
        int dest = grant->getDestONU();
        if (dest >= 0 && dest < numONUs) {
            send(grant, "onuPort$o", dest);
        } else {
            EV_WARN << "Splitter: destino ONU inválido " << dest << "\n";
            delete msg;
        }
    } else {
        send(msg, "oltPort$o");
    }
}

} // namespace pon_dba_sim
