"""Oracle verifier for git-hunt-001."""

import os
import re
import sys


def main() -> int:
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as fh:
            output = fh.read()
    else:
        output = os.environ.get("AGENT_OUTPUT", "")

    match = re.search(r"\b[0-9a-f]{40}\b", output)
    if not match:
        print("FAIL: no full commit SHA in agent output")
        return 1
    with open("/root/.real_answer") as fh:
        expected = fh.read().strip()
    if match.group(0) == expected:
        print("PASS")
        return 0
    print("FAIL: SHA does not match ground truth")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
