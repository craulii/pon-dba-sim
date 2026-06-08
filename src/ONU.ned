// Módulo ONU (Optical Network Unit) — genera tráfico y lo envía en slots asignados
// Proyecto TEL-341 — OmneTeam

package pon_dba_sim;

simple ONU {
    parameters:
        @class(pon_dba_sim::ONU);
        int onuId;
        int bufferSize_eMBB   = default(1048576);
        int bufferSize_URLLC  = default(102400);
        int bufferSize_mMTC   = default(512000);
        double dataRate @unit(bps) = default(1Gbps);
        double guardTime @unit(s) = default(1us);
        double embbRate @unit(bps) = default(100Mbps);
        double urllcRate @unit(bps) = default(5Mbps);
        double mmtcRate @unit(bps) = default(0.5Mbps);
        double urllcDeadline @unit(s) = default(250us);
        @display("i=device/modem;is=s");

    gates:
        inout ponPort;
}
