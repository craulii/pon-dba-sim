// Módulo OLT (Optical Line Terminal) — motor del algoritmo DBA
// Proyecto TEL-341 — OmneTeam

package pon_dba_sim;

simple OLT {
    parameters:
        @class(pon_dba_sim::OLT);
        string dbaAlgorithm = default("IPACT");
        int numONUs = default(16);
        int maxGrantSize = default(64000);
        double pollingCycleTime @unit(s) = default(2ms);
        double guardTime @unit(s) = default(1us);
        double dataRate @unit(bps) = default(1Gbps);
        double wfqWeightEMBB = default(0.7);
        double wfqWeightMMTC = default(0.3);
        @display("i=device/server2;is=l;bgb=60,60");

    gates:
        inout ponPort;
}
