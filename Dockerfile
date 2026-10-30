FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# OTIO is a small optional interchange adapter used to export editable timelines.
RUN python -m pip install --no-cache-dir opentimelineio==0.18.1
COPY . .
RUN useradd --create-home --uid 10001 studio && mkdir -p /data && chown -R studio:studio /data /app
USER studio
ENV CINEMA_WORKSPACE=/data
EXPOSE 10000
CMD ["sh","-c","exec python studio_web.py --host 0.0.0.0 --port ${PORT:-10000} --workspace ${CINEMA_WORKSPACE:-/data}"]
