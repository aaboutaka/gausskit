%Chk=H2_HF_genecp.chk
#P HF/genecp Opt Freq SCF=(fermi, novaracc) int=superfinegrid

Benchmark calculation for H2

0 1
H 0.000000 0.000000 0.000000
H 0.000000 0.000000 0.740000

@SDDPlusTZ.gbs

--Link1--
%OldChk=H2_HF_genecp.chk
%Chk=H2_HF_genecp-stab.chk
#P HF/genecp chkbasis Geom=AllCheck Guess=Read Stable=Opt

