#!/bin/bash
#SBATCH --mail-user=$USER@ucmerced.edu
#SBATCH --mail-type=ALL
#SBATCH -J H2O_CAMB3LYP_genecp
#SBATCH -o H2O_CAMB3LYP_genecp.com.qlog
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
gdv -m=92GB -p=56 < H2O_CAMB3LYP_genecp.com >& H2O_CAMB3LYP_genecp.log

# Clean up
rm -rf $My_Scratch

# Created at 2025-08-02 15:31:43
