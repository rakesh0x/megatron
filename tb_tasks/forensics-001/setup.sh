#!/bin/bash
# Build the vault maze. Runs once at image build time as root.
set -euo pipefail

rm -rf /srv/vault && mkdir -p /srv/vault

REAL=$(openssl rand -hex 16)
SUM=$(echo -n "$REAL" | sha256sum | cut -d' ' -f1)
D=$(printf '/srv/vault/layer%02d/sublayer%02d' $((RANDOM % 20)) $((RANDOM % 20)))
mkdir -p "$D"
printf '%s\n%s\n' "$REAL" "$SUM" > "$D/ledger.dat"
touch -d '2023-06-15 10:00:00' "$D/ledger.dat"
echo "$REAL" > /root/.real_token
chmod 600 /root/.real_token

for i in $(seq 1 250); do
  F=$(printf '/srv/vault/layer%02d/sublayer%02d/decoy_%03d.log' \
    $((RANDOM % 20)) $((RANDOM % 20)) "$i")
  mkdir -p "$(dirname "$F")"
  case $((RANDOM % 4)) in
    0) FAKE=$(openssl rand -hex 16 | tr 'a-f' 'A-F');;
    1) FAKE=$(openssl rand -hex 15);;
    2) FAKE=$(openssl rand -hex 16);;
    *) FAKE="not-a-token-$RANDOM";;
  esac
  printf '%s\n%s\n' "$FAKE" "$(openssl rand -hex 32)" > "$F"
  touch -d '2024-06-01 10:00:00' "$F"
done
