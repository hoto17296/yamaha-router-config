FROM debian:13

WORKDIR /workspace

# Common Packages
RUN apt-get update \
  && apt-get install -y --no-install-recommends git openssh-client \
  && rm -rf /var/lib/apt/lists/*

# Python
COPY --from=ghcr.io/astral-sh/uv /uv /usr/local/bin/uv
RUN uv python install 3.14
ENV UV_PROJECT=/workspace
ENV PATH=${UV_PROJECT}/.venv/bin:${PATH}