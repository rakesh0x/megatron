#!/bin/bash
# Reference solution: IPs with >=2 checkout-500s followed by a checkout-200.
set -euo pipefail
awk '$6=="/checkout" && $8==500 {n500[$1]++; last500[$1]=NR}
     $6=="/checkout" && $8==200 && ($1 in last500) {ok[$1]=NR}
     END {for (ip in ok) if (n500[ip]>=2 && ok[ip]>last500[ip]) print ip}' \
  /srv/logs/access.log
