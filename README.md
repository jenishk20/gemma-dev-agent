# gemma-dev-agent

Work for Kaggle's **Gemma 4 Developer Agent** competition (deadline Dec 2, 2026), plus the earlier BaxBench paper experiment.

| Folder | What |
|---|---|
| `submissions/` | Agent configs. Each folder is one submission (`agent.yaml` at its root); `tools/build_notebook.py` turns it into a `.zip` + Kaggle notebook |
| `tools/validate_submission.py` | Runs the competition's own checks on a zip before spending a submission |
| `tools/run_local_eval.py` | Scores a submission on the public tasks exactly like Kaggle (vLLM + swegemma, subprocess sandbox) |
| `cluster/` | H200 setup and eval jobs |
| `kernels/` | Kaggle notebook metadata for submitting |
| `secure-backends/` | BaxBench security paper experiment (history kept) |
| `kaggle_data/` | Small competition files for local use (gitignored) |

Secrets live in `.env` (gitignored). Never commit it.

## Cluster workflow

Code goes Mac → GitHub → cluster; data and models are downloaded on the cluster, never committed.

```bash
# once, on the cluster
cd /scratch/$USER && git clone git@github.com:jenishk20/gemma-dev-agent.git && cd gemma-dev-agent
# once, from the Mac:  scp .env <you>@<cluster>:/scratch/<you>/gemma-dev-agent/
sbatch cluster/setup.sh            # Kaggle's packages + 22 GB data + E4B weights into /scratch/$USER/gda
sbatch cluster/eval.sbatch         # smoke test: E4B baseline on 10 tasks

# every time
git pull && SUB=submissions/<name> N=0 sbatch cluster/eval.sbatch   # N=0 = all 129 tasks
```

**From OOD Job Composer** (no `sbatch` in the Apptainer shell): paste `cluster/ood_eval.sh` as the job script once, edit its
`SUB` / `N` / `C` lines per run, and submit. It runs the repo's `cluster/eval.sbatch`, so a `git pull` is enough to pick up fixes.
Logs always land in `/scratch/phalle.y/gemma-dev-agent/gda-eval_<jobid>.out`, whichever way you submit.

Before the first run, accept the Gemma 4 license on its Kaggle model page (kaggle.com/models/google/gemma-4), or the weight download is refused.
