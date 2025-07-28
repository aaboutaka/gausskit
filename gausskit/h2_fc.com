%oldchk=h2o_anion.chk
%chk=h2_fc.chk
#p HF ChkBasis FREQ(ReadFC,FC,ReadFCHT) Geom=Checkpoint NOSYMM guess=read

h2 Franck–Condon calculation

-1 2

Spectrum=(VerticalHessian,Broadening=Stick,Lower=-10000.0,Upper=40000.0) temperature=5.0



