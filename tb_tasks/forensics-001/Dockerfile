FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    findutils \
    grep \
    openssl \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# World setup: vault maze with one real token + 250 decoys.
COPY setup.sh /usr/local/bin/setup.sh
RUN chmod +x /usr/local/bin/setup.sh && /usr/local/bin/setup.sh

# Agent runs unprivileged: can read the vault, cannot read the answer.
RUN useradd -m agent && chmod 700 /root
USER agent
WORKDIR /home/agent
