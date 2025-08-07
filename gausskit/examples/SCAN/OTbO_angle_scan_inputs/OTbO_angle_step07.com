%chk=OTbO_angle_step07.chk
#P B3LYP Genecp scf=novaracc

OTbO_angle_step07

0 15
Tb
O  1  R1
Tb 2  R2  1  A1

R1=1.9
R2=1.9
A1=170.000000

@SDDPlusTZ.gbs
