%chk=HOH_angle_step06.chk
#P B3LYP genecp scf=novaracc

HOH_angle_step06

0 1
O
H     1   R1
H     1   R1   2   A1

R1=0.96
A1=125.000000

@SDDPlusTZ.gbs
