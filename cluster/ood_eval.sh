#!/bin/bash
# Paste THIS into OOD Job Composer (once). It only sets Slurm resources and the three knobs below,
# then runs cluster/eval.sbatch from the repo, so `git pull` updates the logic without re-pasting.
# Log: /scratch/phalle.y/gemma-dev-agent/gda-eval_<jobid>.out
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --gres=gpu:h200:1
#SBATCH --time=06:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=16
#SBATCH --job-name=gda-eval
#SBATCH --output=/scratch/phalle.y/gemma-dev-agent/gda-eval_%j.out

export SUB=submissions/e4b_baseline   # which agent folder to score
export N=10                           # number of tasks (0 = all 129)
export C=8                            # tasks run at the same time
bash /scratch/phalle.y/gemma-dev-agent/cluster/eval.sbatch
