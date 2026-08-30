# Sentio B2B / Auth service -> https://b2bapi.sentiomind.in (Google Cloud Run)
#
# This image builds the AUTH service only. It installs requirements.txt and
# never requirements-cv.txt, so OpenCV / DeepFace / MediaPipe / face_recognition
# / MTCNN / TensorFlow are absent by construction — that is the CV separation,
# and it is what keeps this image ~200MB instead of ~4GB.
#
# Build (from the Backend/ directory):
#   docker build -t b2b-auth .
# Run locally the way Cloud Run runs it:
#   docker run -p 8080:8080 --env-file .env b2b-auth

# ---------- stage 1: build wheels -------------------------------------------
# psycopg2-binary and cryptography ship manylinux wheels, but building in a
# separate stage keeps compilers and build headers out of the runtime image.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/pip install -r requirements.txt

# ---------- stage 2: runtime -------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    FLASK_ENV=production

# libpq5 is psycopg2's runtime shared library; curl is only for the HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin sentio

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Only what the auth service actually imports. cv_analysis/, test_db.py, the
# media directories and the test suite are all excluded (see .dockerignore),
# so a stray `import cv_analysis` fails loudly in CI rather than quietly
# dragging the CV stack back into this image.
COPY --chown=sentio:sentio app_factory.py wsgi_auth.py gunicorn_config.py ./
COPY --chown=sentio:sentio auth/ ./auth/
COPY --chown=sentio:sentio common/ ./common/

USER sentio

EXPOSE 8080

# Cloud Run ignores this and uses its own probes; it makes `docker run` and
# Compose behave the same way.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# Gunicorn, never Flask's development server. gunicorn_config.py binds
# 0.0.0.0:$PORT, which is what Cloud Run requires.
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi_auth:app"]
