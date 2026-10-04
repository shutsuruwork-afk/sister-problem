# Executor procedure (for a Claude Code session on the GPU machine)

This file is for a Claude Code session started **on the user's own machine**
(the one with the GPU), e.g. `claude --model claude-sonnet-5-5` in this folder.
Its only job is to run experiments and hand the results back through git.
The research itself is done elsewhere; do not change engine or research code.

## Each time you are asked to run

1. `git pull origin claude/antigravity-research-progress-ugqfqc`
2. Open `RESEARCH_LOG.md` and find the section **「次の GPU 実行」**. Run exactly the
   command written there.  If there is none, run `python local/run_local.py`.
3. When it finishes (or fails), copy the newest `results/run_*.json` to
   `results/<YYYY-MM-DD>_<gpu-model>_run<N>.json` (lower case, no spaces,
   N = next free number).  Also save the full console output next to it as
   `.txt`.
4. Redact personal paths in both files: replace `C:\Users\<name>` (or
   `/home/<name>`) with `C:\Users\<user>`.  Do not record host names.
5. `git add results/<the two files>` and commit with the message
   `Add GPU run <N> results (<gpu-model>)`, then
   `git push origin claude/antigravity-research-progress-ugqfqc`.
6. Report to the user in two or three lines.  **Start with the short commit
   sha of your push** (the user relays it to the research session, which
   reads everything else from git), then: did steps 2 and 3 of the runner
   pass, and whether a target value matched.

(A session on this machine cannot see the cloud research session in
`ListAgents`, so there is no direct notice; the user passes the sha on.)

## Never

- edit anything under `kaggle/`, `research/`, `local/`, or the `.md` logs
- force-push, rebase, or push to any other branch
- try to "fix" a failing kernel; a failure with its traceback **is** a result,
  commit it like any other
- delete `results/` files
