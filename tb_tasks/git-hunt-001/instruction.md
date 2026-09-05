# Find the Commit That Broke the Build

The repository at `/srv/shop/` is a small Python project with ~40 commits.
At some point, a commit changed the constant `TAX_RATE` in `pricing.py`
from its original value to a wrong one. Every commit after that inherited
the bug.

1. Find the **first** commit (oldest in history) where `pricing.py`
   contains the wrong `TAX_RATE`.
2. Print **only** the full 40-character SHA of that commit to stdout.

Constraints: do not modify the repository. Read-only forensics.
