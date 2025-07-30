%Chk=H2_CAMB3LYP_STO3G.chk
#P CAM-B3LYP/STO-3G Opt Freq SCF=(fermi, novaracc) int=superfinegrid

Benchmark calculation for H2

0 1
H 0.000000 0.000000 0.000000
H 0.000000 0.000000 0.740000

@SDDPlusTZ.gbs

--Link1--
%OldChk=H2_CAMB3LYP_STO3G.chk
%Chk=H2_CAMB3LYP_STO3G-stab.chk
#P CAM-B3LYP/STO-3G chkbasis Geom=AllCheck Guess=Read Stable=Opt

