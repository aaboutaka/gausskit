%chk=H2_HF_STO-3G_q0_m1_stab.chk
#p HF/STO-3G stable=opt scf=novaracc guess=mix int=superfinegrid

H2 — HF/STO-3G   q=0 m=1   [1/3: Stability]

0 1
H   0.00000000  0.00000000  0.00000000
H   0.00000000  0.00000000  0.74000000

--Link1--
%oldchk=H2_HF_STO-3G_q0_m1_stab.chk
%chk=H2_HF_STO-3G_q0_m1.chk
#p HF guess=read chkbasis geom=allcheck Opt Freq int=superfinegrid scf=xqc

H2 — HF/STO-3G   q=0 m=1   [2/3: Opt+Freq]

--Link1--
%oldchk=H2_HF_STO-3G_q0_m1.chk
%chk=H2_HF_STO-3G_q0_m1_stab.chk
#p HF stable=opt guess=read chkbasis geom=allcheck int=superfinegrid

H2 — HF/STO-3G   q=0 m=1   [3/3: Stability]

