#!/bin/bash
# Reference solution: proves the task is solvable.
set -euo pipefail

find /srv/vault -type f | while read -r f; do
  # Candidate must be old enough.
  if [[ $(stat -c %y "$f") > "2024-01-01" ]]; then
    continue
  fi
  token=$(sed -n '1p' "$f")
  expect=$(sed -n '2p' "$f")
  # Must be 32-char lowercase hex.
  if ! [[ $token =~ ^[a-f0-9]{32}$ ]]; then
    continue
  fi
  actual=$(echo -n "$token" | sha256sum | cut -d' ' -f1)
  if [[ $actual == "$expect" ]]; then
    echo "$token"
    exit 0
  fi
done
exit 1
