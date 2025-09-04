%chk=H2O_B3LYP_STO-3G_q0_m1_stab.chk
#p B3LYP/STO-3G stable=opt scf=novaracc guess=mix int=superfinegrid

H2O — B3LYP/STO-3G   q=0 m=1   [1/3: Stability]

0 1
O   0.00000000  0.00000000  0.00000000
H   0.75860200  0.00000000  0.50428400
H  -0.75860200  0.00000000  0.50428400

--Link1--
%oldchk=H2O_B3LYP_STO-3G_q0_m1_stab.chk
%chk=H2O_B3LYP_STO-3G_q0_m1.chk
#p B3LYP guess=read chkbasis geom=allcheck Opt Freq int=superfinegrid scf=xqc

H2O — B3LYP/STO-3G   q=0 m=1   [2/3: Opt+Freq]

--Link1--
%oldchk=H2O_B3LYP_STO-3G_q0_m1.chk
%chk=H2O_B3LYP_STO-3G_q0_m1_stab.chk
#p B3LYP stable=opt guess=read chkbasis geom=allcheck int=superfinegrid

H2O — B3LYP/STO-3G   q=0 m=1   [3/3: Stability]

