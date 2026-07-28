FROM python:3.11-alpine

ARG BUILD_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/mwoDevelop/script.module.mwoscrapers"
LABEL org.opencontainers.image.revision="${BUILD_REVISION}"

RUN addgroup -S relay && adduser -S -G relay -u 10001 relay
WORKDIR /app
COPY relay/mwoscrapers_relay /app/mwoscrapers_relay

USER 10001:10001
EXPOSE 8766
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8766/health', timeout=2))['status'] == 'ok'"
ENTRYPOINT ["python", "-m", "mwoscrapers_relay.server"]
