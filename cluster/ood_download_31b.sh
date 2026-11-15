#!/bin/bash
# Paste THIS into OOD Job Composer to download the 31B weights (23 GB, CPU only, ~30-60 min).
# Re-runs the one-time setup with the 31B model added; steps already done (venv, data, test libraries) are skipped.
# Log: /scratch/phalle.y/gemma-dev-agent/gda-setup_<jobid>.out
#SBATCH --partition=short
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --job-name=gda-setup
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-setup_%j.out

export MODELS="gemma-4-31b-it-qat-w4a16-ct"
bash /scratch/phalle.y/gemma-dev-agent/cluster/setup.sh
