# RailVigil

Automated Railway Track Encroachment Detection Using YOLOv8 Video Analytics.

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

This repository is a structural scaffold. Modules contain placeholder functions/classes only; implementation is intentionally left for the development phase.
