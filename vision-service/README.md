# ARGUS Vision Worker
Run from repository root: `.venv/bin/python -m backend.argus.worker`.
Implementation is in `backend/argus/worker.py`, sharing database contracts with the API. It runs in a separate process/container, claims durable jobs atomically, persists progress, writes sampled observations and event snapshots. Detector/tracker contracts live in `backend/argus/vision.py`.
