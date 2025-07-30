%Chk=H2O_B3LYP_631pGdp.chk
#P B3LYP/6-31+G(d,p) Opt Freq SCF=(fermi, novaracc) int=superfinegrid

Benchmark calculation for H2O

0 1
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284

@SDDPlusTZ.gbs

--Link1--
%OldChk=H2O_B3LYP_631pGdp.chk
%Chk=H2O_B3LYP_631pGdp-stab.chk
#P B3LYP/6-31+G(d,p) chkbasis Geom=AllCheck Guess=Read Stable=Opt

