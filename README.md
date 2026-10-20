# RailVigil

Automated railway **intrusion** detection using YOLOv8 video analytics — people, animals, and vehicles entering configured track-side safety zones. Physical encroachment (structures, vegetation, debris) is out of scope for the current pipeline.

## Project Structure

- `backend/` — FastAPI backend, computer-vision pipeline, API, database layer, tests, data and model locations.
- `frontend/` — React + Vite dashboard and monitoring interface.

## Run the backend

From `RailVigil/backend`:

```bash
python -m venv .venv
.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run the frontend

From `RailVigil/frontend`:

```bash
npm install
npm run dev
```

## Notes

Stage 2 focuses on **reliable intrusion detection and video processing** (queue, validation, migrations, shared zone resolution). Do not treat missing zones as the whole frame — provide a drawn zone, `.zone.json` sidecar, or `CAMERA_ZONES` config.
