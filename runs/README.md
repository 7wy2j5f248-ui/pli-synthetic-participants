# Runs

Create one folder per run:

```text
runs/R001/
  manifest.md
  progress.csv
```

Copy the two files from `templates/`, replace their example values, and ask Claude to execute that manifest. Keep hidden persona cards out of this folder. PLI transcripts may live in PLI itself or another approved destination; the progress file stores only their stable references.

Allowed status values: `pending`, `in_progress`, `completed`, `blocked`.
