%oldchk=h2o_neutral.chk
%chk=h2o_neutral-a4_6.chk
#p uwb97xd scf=(pimom,fermi,novaracc) integral=SuperFineGrid guess=(alter,read) geom=check chkbasis

Title Card Required

0 1

4 6 ! alpha swap


