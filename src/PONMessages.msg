// Definición de mensajes para simulación PON DBA
// Proyecto TEL-341 — OmneTeam

cplusplus {{
#include <omnetpp.h>
using namespace omnetpp;
}}

namespace pon_dba_sim;

// Paquete de datos generado por las ONUs (tráfico upstream)
// trafficClass=0→verde(eMBB), 1→rojo(URLLC), 2→naranja(mMTC)
packet DataPacket {
    @display("i=msg/packet");
    int sourceONU;
    int trafficClass;       // 0=eMBB, 1=URLLC, 2=mMTC
    simtime_t creationTime; // para calcular latencia end-to-end
    simtime_t deadline;     // solo URLLC (250us), -1 para otros
    int dataSize;           // bytes
}

// Reporte de ONU a OLT: cuántos bytes tiene en cada cola
message ReportMessage {
    @display("i=msg/report");
    int sourceONU;
    int queueSize_eMBB;     // bytes pendientes eMBB
    int queueSize_URLLC;    // bytes pendientes URLLC
    int queueSize_mMTC;     // bytes pendientes mMTC
}

// Grant de OLT a ONU: slot de transmisión asignado
message GrantMessage {
    @display("i=msg/token");
    int destONU;
    simtime_t startTime;    // inicio absoluto del slot
    int grantSize_eMBB;     // bytes autorizados eMBB
    int grantSize_URLLC;    // bytes autorizados URLLC
    int grantSize_mMTC;     // bytes autorizados mMTC
}
