%oldchk=h2o_anion.chk
%chk=h2o_anion_fc.chk
#p wb97xd ChkBasis FREQ(ReadFC,FC,ReadFCHT) Geom=Checkpoint NOSYMM guess=read

h2o_anion Franck–Condon calculation

-1 2

 Method=AdiabaticHessian, Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) temperature=300

test

