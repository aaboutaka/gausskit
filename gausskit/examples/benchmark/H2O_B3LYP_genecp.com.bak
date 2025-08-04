%Chk=H2O_B3LYP_genecp.chk
#P B3LYP/genecp SCF=(fermi,novaracc) Guess=Mix Stable=Opt scf=(qc,conver=8) scf=qc int=ultrafine scf=novaracc

Initial Stability Check for H2O

0 1
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284

@SDDPlusTZ.gbs

--Link1--
%Chk=H2O_B3LYP_genecp.chk
#P B3LYP chkbasis Geom=AllCheck Guess=Read Opt Freq SCF=(fermi, novaracc) int=superfinegrid scf=(qc,conver=8) scf=qc int=ultrafine scf=novaracc

Optimization and Frequency

--Link1--
%OldChk=H2O_B3LYP_genecp.chk
%Chk=H2O_B3LYP_genecp-stab.chk
#P B3LYP chkbasis Geom=AllCheck Guess=Read Stable=Opt SCF=(fermi,novaracc) scf=(qc,conver=8) scf=qc int=ultrafine scf=novaracc

Final Stability Check

