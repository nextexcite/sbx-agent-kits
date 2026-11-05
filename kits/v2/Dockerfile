# syntax=docker/dockerfile:1
# Real OCI runtime image for the v2 kit. The v2 descriptor is a separate artifact.
ARG BASE_IMAGE=dhi.io/sbx-templates:shell-docker
FROM ${BASE_IMAGE}
USER root
COPY scripts/install-toolchains.sh /opt/sbx-agent-kits/install-toolchains.sh
COPY scripts/refresh-node-lts.sh /usr/local/bin/refresh-node-lts
COPY scripts/verify-runtime.sh /usr/local/bin/sbx-agent-kits-verify
RUN chmod 0755 /opt/sbx-agent-kits/install-toolchains.sh /usr/local/bin/refresh-node-lts /usr/local/bin/sbx-agent-kits-verify \
 && /opt/sbx-agent-kits/install-toolchains.sh system
ENV FNM_DIR=/home/agent/.local/share/fnm \
    PATH=/home/agent/.local/bin:/home/agent/.local/share/fnm/current-bin:/home/agent/.local/npm/bin:/home/agent/.bun/bin:/home/agent/.deno/bin:${PATH} \
    AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium \
    IS_SANDBOX=1
USER agent
RUN /opt/sbx-agent-kits/install-toolchains.sh user
WORKDIR /home/agent/workspace
LABEL com.docker.sandboxes.flavor="amp"
LABEL com.docker.sandboxes.start-docker="true"
LABEL org.opencontainers.image.source="https://github.com/nextexcite/sbx-agent-kits"
ENTRYPOINT ["amp"]
# Clear any CMD inherited from the shell template: no extra argv to Amp.
CMD []
