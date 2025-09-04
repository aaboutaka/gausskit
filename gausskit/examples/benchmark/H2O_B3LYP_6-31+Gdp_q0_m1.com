%chk=H2O_B3LYP_6-31+Gdp_q0_m1.chk
#p B3LYP/6-31+G(d,p) stable=opt scf=novaracc guess=mix

H2O — B3LYP/6-31+G(d,p)   q=0 m=1   [1/3: Stability]

0 1
O   0.00000000  0.00000000  0.00000000
H   0.75860200  0.00000000  0.50428400
H  -0.75860200  0.00000000  0.50428400

--Link1--
%chk=H2O_B3LYP_6-31+Gdp_q0_m1.chk
#p B3LYP guess=read chkbasis geom=allcheck Opt Freq SCF=(fermi, novaracc) int=superfinegrid

H2O — B3LYP/6-31+G(d,p)   q=0 m=1   [2/3: Opt+Freq]

--Link1--
%chk=H2O_B3LYP_6-31+Gdp_q0_m1.chk
#p B3LYP stable=opt guess=read chkbasis geom=allcheck

H2O — B3LYP/6-31+G(d,p)   q=0 m=1   [3/3: Stability]

