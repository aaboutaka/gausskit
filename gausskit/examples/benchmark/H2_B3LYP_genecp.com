%Chk=H2_B3LYP_genecp.chk
#P B3LYP/genecp SCF=(fermi,novaracc) Guess=Mix Stable=Opt

Initial Stability Check for H2

0 1
H 0.000000 0.000000 0.000000
H 0.000000 0.000000 0.740000

@SDDPlusTZ.gbs

--Link1--
%Chk=H2_B3LYP_genecp.chk
#P B3LYP chkbasis Geom=AllCheck Guess=Read Opt Freq SCF=(fermi, novaracc) int=superfinegrid

Optimization and Frequency

--Link1--
%OldChk=H2_B3LYP_genecp.chk
%Chk=H2_B3LYP_genecp-stab.chk
#P  B3LYP chkbasis  Geom=AllCheck Guess=Read Stable=Opt SCF=(fermi,novaracc)

Final Stability Check



