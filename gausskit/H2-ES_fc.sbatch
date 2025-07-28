#!/bin/bash
#SBATCH --mail-user=$USER@ucmerced.edu
#SBATCH --mail-type=ALL
#SBATCH -J H2-ES_fc
#SBATCH -o H2-ES_fc.com.qlog
#SBATCH -p cenvalarc.bigmem
#SBATCH --time=23:50:00
#SBATCH --mem=115200
#SBATCH --nodes=1
#SBATCH --ntasks=56

# Load Gaussian module
module load gaussian/gdv-20250101-j30+

# Scratch directory setup
export My_Scratch=/scratch/$USER/$SLURM_JOBID
export GAUSS_SCRDIR=$My_Scratch
mkdir -p $My_Scratch

# Run Gaussian
gdv -m=92GB -p=56 < H2-ES_fc.com >& H2-ES_fc.log

# Clean up
rm -rf $My_Scratch

# Created at 2025-07-28 13:06:14
