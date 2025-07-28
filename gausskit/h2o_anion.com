%oldchk=h2o_neutral.chk.chk
%chk=h2o_anion.chk.chk
#p HF ChkBasis FREQ(ReadFC,FC,ReadFCHT) Geom=Checkpoint NOSYMM guess=read

h2o_anion Franck–Condon calculation

-1 2

Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) temperature=5.0



