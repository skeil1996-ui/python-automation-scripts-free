# Git Branch Cleanup Tool – Lite (free)

A small, dependency-free Python tool that finds and removes already-merged local Git branches.

## Usage

```
python tool.py                       # dry run in current repo, base branch "main"
python tool.py --repo /path/to/repo --base develop
python tool.py --delete              # actually delete (git branch -d)
```

Safe by design: dry run by default, only `git branch -d` is used (never `-D`), and the base and current branches are never touched.

## Lite limitations

- Local branches only (no remote deletion)
- Max 5 branches per run
- No age filter, no `--keep` patterns, no JSON output

## Full version

Age filter, keep patterns, remote deletion, JSON output and no branch limit:
https://skeilster.gumroad.com/l/uvpwln

## Requirements

Python 3.8+ and `git` in your PATH. Run tests with `python -m unittest`.

Exit codes: `0` ok, `1` error, `2` base branch missing, `4` some deletions failed.
