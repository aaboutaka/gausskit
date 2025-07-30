#!/bin/bash
#SBATCH --mail-user=$USER@ucmerced.edu
#SBATCH --mail-type=ALL
#SBATCH -J ch2o_neutral
#SBATCH -o ch2o_neutral.com.qlog
#SBATCH -p test
#SBATCH --time=00:10:00
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
gdv -m=92GB -p=56 < ch2o_neutral.com >& ch2o_neutral.log

# Clean up
rm -rf $My_Scratch

# Created at 2025-07-30 07:40:08
