// Splitter pasivo 1:N
// Proyecto TEL-341 — OmneTeam

package pon_dba_sim;

simple Splitter {
    parameters:
        @class(pon_dba_sim::Splitter);
        int numONUs = default(16);
        @display("i=device/opticalswitch;is=n");

    gates:
        inout oltPort;
        inout onuPort[numONUs];
}
