"""Oracle verifier for forensics-001.

Runs the agent's stdout (captured to $AGENT_OUTPUT_FILE by the harness,
or passed as argv[1]) against the ground-truth token baked into the
image at /root/.real_token.
"""

import os
import re
import sys


def main() -> int:
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as fh:
            output = fh.read()
    else:
        output = os.environ.get("AGENT_OUTPUT", "")

    candidates = re.findall(r"[a-f0-9]{32}", output)
    if not candidates:
        print("FAIL: no 32-char hex token in agent output")
        return 1

    with open("/root/.real_token") as fh:
        expected = fh.read().strip()

    if candidates[0] == expected:
        print("PASS")
        return 0
    print("FAIL: token does not match ground truth")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
