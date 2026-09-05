FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    gawk \
    grep \
    python3 \
    && rm -rf /var/lib/apt/lists/*

COPY setup.sh /usr/local/bin/setup.sh
RUN chmod +x /usr/local/bin/setup.sh && /usr/local/bin/setup.sh

RUN useradd -m agent && chmod 700 /root
USER agent
WORKDIR /home/agent
