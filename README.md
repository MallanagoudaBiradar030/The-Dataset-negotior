# AI Dataset Negotiator

Find and compare datasets using a natural-language description of a machine-learning task. Search results come from Hugging Face, Kaggle, and the UCI Machine Learning Repository; unavailable providers are reported instead of replaced with sample results.

## Project layout

```text
backend/app/
  api/routes.py
  models/schemas.py
  providers/{huggingface,kaggle,uci}.py
  services/{compatibility,comparison,dataset_search,download,filtering,
            quality_analysis,recommendation,task_understanding}.py
  main.py
backend/tests/test_services.py
src/{App.tsx,main.tsx,style.css,types.ts}
```

## Install

Use Python 3.11+ and Node.js 20+.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
npm install
```

Set `KAGGLE_USERNAME` and `KAGGLE_KEY` in `.env` to enable Kaggle search and downloads. Hugging Face and UCI search are public. `FRONTEND_ORIGIN` controls the permitted browser origin. Set frontend API origin with `VITE_API_URL` if the backend is not at `http://localhost:8000`.

## Run manually

Start the backend from the repository root with `uvicorn app.main:app --app-dir backend --reload`. In another terminal, run `npm run dev`. The API schema is available at `/docs` while the backend is running.

## API

- `GET /api/health`
- `POST /api/task/understand` — body: `{"description":"..."}`
- `POST /api/datasets/search` and `POST /api/datasets/recommend` — description, source selection, result limit, and optional metadata filters
- `POST /api/datasets/compare` — one to five dataset objects
- `GET /api/datasets/{dataset_id}` — fetch current provider metadata by source-prefixed ID
- `GET /api/datasets/{dataset_id}/download` — stream a supported provider download
- `POST /api/datasets/{dataset_id}/download` — download using metadata returned by search

Recommendation scores use task relevance (30%), token similarity (25%), feature compatibility (20%), domain relevance (15%), and metadata completeness (10%). Unknown metadata is not treated as verified. Quality analysis describes metadata only; it does not inspect dataset contents. Download requests are streamed with a 100 MB cap; Kaggle requires credentials, and direct downloads are exposed only when a provider returns a supported URL.

## Checks

```sh
pytest -q backend/tests
npm run typecheck
npm run build
```

Provider search failures are isolated and returned in the response's `providers` map. Search results and recommendations are not persisted.
