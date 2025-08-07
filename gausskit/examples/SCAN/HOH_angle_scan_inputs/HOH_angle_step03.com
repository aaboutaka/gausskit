%chk=HOH_angle_step03.chk
#P B3LYP genecp scf=novaracc

HOH_angle_step03

0 1
O
H     1   R1
H     1   R1   2   A1

R1=0.96
A1=110.000000

@SDDPlusTZ.gbs
