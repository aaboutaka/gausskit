%Chk=H2_CAMB3LYP_631pGdp.chk
#P CAM-B3LYP/6-31+G(d,p) Opt Freq SCF=(fermi, novaracc) int=superfinegrid

Benchmark calculation for H2

0 1
H 0.000000 0.000000 0.000000
H 0.000000 0.000000 0.740000

@SDDPlusTZ.gbs

--Link1--
%OldChk=H2_CAMB3LYP_631pGdp.chk
%Chk=H2_CAMB3LYP_631pGdp-stab.chk
#P CAM-B3LYP/6-31+G(d,p) chkbasis Geom=AllCheck Guess=Read Stable=Opt

