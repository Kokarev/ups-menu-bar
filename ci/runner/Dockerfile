FROM ghcr.io/actions/actions-runner:2.338.2
USER root
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends nut-server nut-client python3 python3-tk python3-pil xvfb xauth git ca-certificates && rm -rf /var/lib/apt/lists/*
USER runner
WORKDIR /home/runner
