# Smart Lagring

Warehouse inventory management: a FastAPI backend (`backend/`) with MongoDB and a Vue 3 + TypeScript
frontend (`frontend/`).

## Backend

```
cd backend
pip install -r requirements.txt
cp .env.example .env        # then fill in MONGODB_URI (and optionally the other values)
cd ..
uvicorn backend.main:app --port 8001   # 8002 works too
```

Tests: `python -m unittest backend.test_damage_reports backend.test_materials backend.test_sessions`

## Frontend

```
cd frontend
npm install
npm run dev
```

The frontend looks for the backend on `http://127.0.0.1:8001` and falls back to `:8002`; set
`VITE_API_BASE_URL` to pin one address.
Before committing: `npm run type-check`, `npm run lint`, `npm run format`.
