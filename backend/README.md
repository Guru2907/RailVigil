# RailVigil Backend

FastAPI service and computer-vision pipelines for RailVigil: intrusion detection in video (working) and physical encroachment detection in images (in development). See the root [README](../README.md).

Install from `backend/`: `pip install -r requirements-dev.txt` (runtime only: `requirements.txt`)
Run from `backend/`: `uvicorn app.main:app --reload`
Check: `pytest` and `ruff check .`

Zones are described in [docs/ZONES.md](../docs/ZONES.md). In short: an upload needs a drawn zone, a `zone_sidecar` JSON field, or a `CAMERA_ZONES` entry for its camera label; the CLI (`scripts/run_clip.py`) reads `<video-stem>.zone.json` when `--zone` is omitted. A missing zone is rejected, never replaced by the whole frame.
