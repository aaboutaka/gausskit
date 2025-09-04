%chk=H2O_CAM-B3LYP_6-31+Gdp_q0_m1_stab.chk
#p CAM-B3LYP/6-31+G(d,p) stable=opt scf=qc guess=mix int=superfinegrid

H2O — CAM-B3LYP/6-31+G(d,p)   q=0 m=1   [1/3: Stability]

0 1
O   0.00000000  0.00000000  0.00000000
H   0.75860200  0.00000000  0.50428400
H  -0.75860200  0.00000000  0.50428400

--Link1--
%oldchk=H2O_CAM-B3LYP_6-31+Gdp_q0_m1_stab.chk
%chk=H2O_CAM-B3LYP_6-31+Gdp_q0_m1.chk
#p CAM-B3LYP guess=read chkbasis geom=allcheck Opt Freq int=superfinegrid scf=xqc

H2O — CAM-B3LYP/6-31+G(d,p)   q=0 m=1   [2/3: Opt+Freq]

--Link1--
%oldchk=H2O_CAM-B3LYP_6-31+Gdp_q0_m1.chk
%chk=H2O_CAM-B3LYP_6-31+Gdp_q0_m1_stab.chk
#p CAM-B3LYP stable=opt guess=read chkbasis geom=allcheck int=superfinegrid

H2O — CAM-B3LYP/6-31+G(d,p)   q=0 m=1   [3/3: Stability]

