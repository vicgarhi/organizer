FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016 AS dependencies
WORKDIR /build
COPY requirements.lock ./
COPY deploy/wheels /wheels
ARG INSTALL_OFFLINE=false
RUN if [ "$INSTALL_OFFLINE" = "true" ]; then \
      (cd /wheels && sha256sum -c SHA256SUMS) && \
      pip install --no-cache-dir --no-index --find-links=/wheels --prefix=/install -r requirements.lock; \
    else \
      pip install --no-cache-dir --prefix=/install -r requirements.lock; \
    fi

FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016
WORKDIR /app
COPY --from=dependencies /install /usr/local
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 static ./static
COPY --chown=10001:10001 scripts ./scripts
RUN useradd --uid 10001 --create-home organizer && mkdir /data && chown organizer /data
USER organizer
ENV DATA_DIR=/data PORT=8000 COOKIE_SECURE=true PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
