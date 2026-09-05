#!/bin/bash
# Build a 40-commit repo; one commit flips TAX_RATE 0.07 -> 0.19.
set -euo pipefail

rm -rf /srv/shop && mkdir -p /srv/shop
cd /srv/shop
git init -q
git config user.email "dev@example.com"
git config user.name "dev"

cat > pricing.py <<'EOF'
TAX_RATE = 0.07

def with_tax(amount):
    return amount * (1 + TAX_RATE)
EOF
git add pricing.py
git commit -qm "initial pricing module"

BREAK_AT=17
for i in $(seq 2 40); do
  echo "# change $i" >> changelog.txt
  git add changelog.txt
  if [ "$i" -eq "$BREAK_AT" ]; then
    sed -i 's/TAX_RATE = 0.07/TAX_RATE = 0.19/' pricing.py
    git add pricing.py
    git commit -qm "update tax tables for Q3"
    git rev-parse HEAD > /root/.real_answer
    chmod 600 /root/.real_answer
  else
    git commit -qm "routine change $i"
  fi
done
chmod -R a+rX /srv/shop
