%Chk=H2O_B3LYP_STO3G.chk
#P B3LYP/STO-3G SCF=(fermi,novaracc) Guess=Mix Stable=Opt

Initial Stability Check for H2O

0 1
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284

--Link1--
%Chk=H2O_B3LYP_STO3G.chk
#P B3LYP chkbasis Geom=AllCheck Guess=Read Opt Freq SCF=(fermi, novaracc) int=superfinegrid

Optimization and Frequency

--Link1--
%OldChk=H2O_B3LYP_STO3G.chk
%Chk=H2O_B3LYP_STO3G-stab.chk
#P  B3LYP chkbasis  Geom=AllCheck Guess=Read Stable=Opt SCF=(fermi,novaracc)

Final Stability Check



