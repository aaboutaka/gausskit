%Chk=H2O_HF_STO3G.chk
#P HF/STO-3G Opt Freq SCF=(fermi, novaracc) int=superfinegrid

Benchmark calculation for H2O

0 1
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284

@SDDPlusTZ.gbs

--Link1--
%OldChk=H2O_HF_STO3G.chk
%Chk=H2O_HF_STO3G-stab.chk
#P HF/STO-3G chkbasis Geom=AllCheck Guess=Read Stable=Opt

