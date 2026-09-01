# AGENTS.md

- For OpenSpec propose/apply/verify/archive workflows, use the local `openspec-git-discipline` skill to enforce proposal commits before apply and merge-before-archive discipline.
- Do not remove any comments in the code, they are there for code explainability
- NEVER do any destructive action without asking the user or unless explicitly asked by user. Including but not limited to:
  - Git commits
  - docker compose down (removing containers)
  - openspec change archive
