#!/bin/bash
#SBATCH --mail-user=aaboutaka@ucmerced.edu
#SBATCH --mail-type=ALL
#SBATCH -J HOH_angle_step07
#SBATCH -o HOH_angle_step07.com.qlog
#SBATCH -p test
#SBATCH --time=00:59:00
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
gdv -m=92GB -p=56 < HOH_angle_step07.com >& HOH_angle_step07.log

# Clean up
rm -rf $My_Scratch

# Created at 2025-08-06 20:06:28
