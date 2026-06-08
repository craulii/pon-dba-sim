// Red PON completa: OLT + Splitter + N ONUs
// Proyecto TEL-341 — OmneTeam

package pon_dba_sim;

network PONNetwork {
    parameters:
        int numONUs = default(16);
        @display("bgb=1100,600");

    submodules:
        olt: OLT {
            @display("p=100,300;i=device/server2;is=l");
        }
        splitter: Splitter {
            numONUs = parent.numONUs;
            @display("p=420,300;i=abstract/opticalswitch;is=n");
        }
        onu[numONUs]: ONU {
            onuId = index;
            @display("p=800,40,col,30;i=device/modem;is=vs");
        }

    connections:
        // Solo delay de propagación — el TDM se garantiza por la lógica del DBA
        olt.ponPort <--> { delay = 100us; } <--> splitter.oltPort;
        for i=0..numONUs-1 {
            splitter.onuPort[i] <--> { delay = 10us; } <--> onu[i].ponPort;
        }
}
