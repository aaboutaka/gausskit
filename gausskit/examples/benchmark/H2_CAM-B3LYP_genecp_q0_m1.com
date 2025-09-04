%chk=H2_CAM-B3LYP_genecp_q0_m1.chk
#p CAM-B3LYP/genecp stable=opt scf=novaracc guess=mix

H2 — CAM-B3LYP/genecp   q=0 m=1   [1/3: Stability]

0 1
H   0.00000000  0.00000000  0.00000000
H   0.00000000  0.00000000  0.74000000

@SDDPlusTZ.gbs
--Link1--
%chk=H2_CAM-B3LYP_genecp_q0_m1.chk
#p CAM-B3LYP guess=read chkbasis geom=allcheck Opt Freq SCF=(fermi, novaracc) int=superfinegrid

H2 — CAM-B3LYP/genecp   q=0 m=1   [2/3: Opt+Freq]

--Link1--
%chk=H2_CAM-B3LYP_genecp_q0_m1.chk
#p CAM-B3LYP stable=opt guess=read chkbasis geom=allcheck

H2 — CAM-B3LYP/genecp   q=0 m=1   [3/3: Stability]

