# Find the Attacker's IP

`/srv/logs/access.log` holds ~6,000 Apache-style access lines from one busy
hour (2024-05-01 10:00–11:00 UTC). Exactly one client IP is malicious:

1. It requested `/checkout` and received HTTP **500** at least twice.
2. It later requested `/checkout` and received HTTP **200** exactly once
   (the successful exploit), AFTER its last 500.
3. No benign IP satisfies both conditions at once: benign traffic never
   produced a 500 on `/checkout`, so only the attacker has 500s there.

Print **only** the attacker's IPv4 address to stdout.
