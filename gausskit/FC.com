%oldchk=h2o_neutral.chk
%chk=h2o_neutral_fc.chk
#P B3LYP/6-31G(d) ChkBasis Freq=(ReadFC,FC,ReadFCHT) Geom=Checkpoint NOSYMM Guess=Read

Franck–Condon Calculation: H2O neutral

0 1

Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) temperature=298.15

h2o_anion.chk

