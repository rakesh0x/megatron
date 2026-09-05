"""Oracle verifier for log-triage-001."""

import os
import re
import sys


def main() -> int:
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as fh:
            output = fh.read()
    else:
        output = os.environ.get("AGENT_OUTPUT", "")

    match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", output)
    if not match:
        print("FAIL: no IPv4 address in agent output")
        return 1
    with open("/root/.real_answer") as fh:
        expected = fh.read().strip()
    if match.group(0) == expected:
        print("PASS")
        return 0
    print("FAIL: IP does not match ground truth")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
