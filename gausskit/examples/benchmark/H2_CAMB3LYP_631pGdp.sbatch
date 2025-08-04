#!/bin/bash
#SBATCH --mail-user=$USER@ucmerced.edu
#SBATCH --mail-type=ALL
#SBATCH -J H2_CAMB3LYP_631pGdp
#SBATCH -o H2_CAMB3LYP_631pGdp.qlog
#SBATCH -p test
#SBATCH --time=00:10:00
#SBATCH --mem=115200
#SBATCH --nodes=1
#SBATCH --ntasks=56

module load gaussian/gdv-20250101-j30+

export My_Scratch=/scratch/$USER/$SLURM_JOBID
export GAUSS_SCRDIR=$My_Scratch
mkdir -p $My_Scratch

gdv -m=92GB -p=56 < H2_CAMB3LYP_631pGdp.com >& H2_CAMB3LYP_631pGdp.log

rm -rf $My_Scratch

# Submitted at 2025-08-04 07:56:01
