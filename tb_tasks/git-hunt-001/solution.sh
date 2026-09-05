#!/bin/bash
# Reference solution: oldest commit containing the wrong rate.
set -euo pipefail
cd /srv/shop
git log --reverse --format=%H -S'TAX_RATE = 0.19' -- pricing.py | head -n 1
