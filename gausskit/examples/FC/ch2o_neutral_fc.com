%oldchk=ch2o_anion.chk
%chk=ch2o_neutral_fc.chk
#P ChkBasis Freq=(ReadFC,FC,ReadFCHT) Geom=Checkpoint NOSYMM Guess=Read

Franck–Condon Calculation: ch2o_neutral

0 1

Spectrum=(Broadening=Stick,Lower=-10000.0,Upper=40000.0) temperature=298.15

ch2o_neutral.chk
