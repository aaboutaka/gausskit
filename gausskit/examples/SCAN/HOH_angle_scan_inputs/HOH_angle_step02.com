%chk=HOH_angle_step02.chk
#P B3LYP genecp scf=novaracc

HOH_angle_step02

0 1
O
H     1   R1
H     1   R1   2   A1

R1=0.96
A1=105.000000

@SDDPlusTZ.gbs
