"""Gunicorn config for production. Run from the Backend directory:

    gunicorn -c gunicorn_config.py wsgi_auth:app        # stakeholder/auth only
    gunicorn -c gunicorn_config.py cv_analysis.app:app  # CV/analysis only
    gunicorn -c gunicorn_config.py test_db:app          # both in one process

The B2B/auth deployment (https://b2bapi.sentiomind.in, Cloud Run) uses
``wsgi_auth:app`` and installs requirements.txt only.

The notes below about heavy native imports, worker count and timeout apply to any
deployment that serves the CV system. An auth-only deployment (wsgi_auth:app)
loads none of that stack and can safely run more workers and the default timeout.

Tuning notes:
  * preload_app is left False: TensorFlow/MediaPipe/dlib initialize native
    (and on GPU hosts, CUDA) state at import time, which does not reliably
    survive fork(). Each worker pays the ~15s heavy-import cost once at
    startup instead.
  * Worker count is deliberately low — DeepFace/TensorFlow/MediaPipe are
    memory-heavy per process. Scale `workers` only after confirming the
    host has RAM for N x (TensorFlow + MediaPipe + face_recognition).
  * timeout is raised well above Gunicorn's 30s default because
    POST /run_analysis performs synchronous CCTV video processing. For real
    production load, move that endpoint to a background worker/queue
    instead of relying on a long HTTP timeout.
"""
import multiprocessing
import os

# Cloud Run routes traffic to the container's own network interface and injects
# $PORT (8080), so the listener must be 0.0.0.0 — a 127.0.0.1 bind makes the
# container fail its startup probe with "the user-provided container failed to
# start and listen on the port". Behind a same-host nginx, set
# GUNICORN_BIND_HOST=127.0.0.1 to keep the socket loopback-only.
_bind_host = os.environ.get("GUNICORN_BIND_HOST", "0.0.0.0")
_port = os.environ.get("PORT", "8080")
bind = os.environ.get("GUNICORN_BIND", f"{_bind_host}:{_port}")

workers = int(os.environ.get("GUNICORN_WORKERS", min(4, multiprocessing.cpu_count())))
threads = int(os.environ.get("GUNICORN_THREADS", 8))
worker_class = "gthread"
preload_app = False
# Auth requests are short; the 300s default exists only for the CV deployment's
# synchronous /run_analysis. Cloud Run caps a request at 3600s anyway.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
# Cloud Run sends SIGTERM and allows ~10s before SIGKILL, so drain inside that.
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 10))
# Must exceed the Google front end's 620s idle keepalive or Cloud Run surfaces
# spurious 502s when it reuses a connection gunicorn has already closed.
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", 650))
max_requests = 500
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
