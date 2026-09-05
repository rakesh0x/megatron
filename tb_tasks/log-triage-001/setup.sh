#!/bin/bash
# Generate a deterministic access log with one planted attacker.
set -euo pipefail
rm -rf /srv/logs && mkdir -p /srv/logs
python3 - <<'EOF'
import random
random.seed(20240501)
paths = ["/", "/products", "/cart", "/checkout", "/login", "/search"]
codes = [200, 200, 200, 200, 301, 404]
ips = [f"10.0.{a}.{b}" for a in range(1, 12) for b in range(1, 21)]
lines = []
t = 10 * 3600
def ts(sec):
    h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"2024-05-01T{h:02d}:{m:02d}:{s:02d}+00:00"
for _ in range(6000):
    ip = random.choice(ips)
    p = random.choice(paths)
    c = random.choice(codes)
    # Keep benign /checkout traffic clean: never 500, never 200-after-500.
    if p == "/checkout":
        c = random.choice([200, 301, 404])
    t += random.randint(0, 2)
    lines.append(f'{ip} - - [{ts(t)}] "GET {p} HTTP/1.1" {c} {random.randint(200, 9000)}')
# Plant the attacker: 3x 500 on /checkout, then 1x 200 afterwards.
attacker = "172.16.9.66"
t += 5
for _ in range(3):
    lines.append(f'{attacker} - - [{ts(t)}] "GET /checkout HTTP/1.1" 500 512')
    t += 7
t += 30
lines.append(f'{attacker} - - [{ts(t)}] "GET /checkout HTTP/1.1" 200 2311')
with open("/srv/logs/access.log", "w") as fh:
    fh.write("\n".join(lines) + "\n")
with open("/root/.real_answer", "w") as fh:
    fh.write(attacker + "\n")
EOF
chmod 600 /root/.real_answer
chmod -R a+rX /srv/logs
