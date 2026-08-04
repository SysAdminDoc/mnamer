FROM python:3.12-slim

ARG MNAMER_VERSION=2.6.1
ARG UID=1000
ARG GID=1000

LABEL org.opencontainers.image.title="mnamer" \
      org.opencontainers.image.description="A command-line utility for organizing media files." \
      org.opencontainers.image.version="${MNAMER_VERSION}"

RUN groupadd --gid "${GID}" mnamer \
    && useradd --uid "${UID}" --gid "${GID}" \
        --create-home --home-dir /home/mnamer --shell /usr/sbin/nologin mnamer \
    && mkdir -p /config /mnt \
    && chown -R "${UID}:${GID}" /config /mnt /home/mnamer

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "mnamer==${MNAMER_VERSION}"

USER mnamer
WORKDIR /config
VOLUME ["/config", "/mnt"]
ENTRYPOINT ["python", "-m", "mnamer"]
CMD ["--batch", "/mnt"]
