# Podcast Study MVP (Next.js + FastAPI + Kokoro)

Convert class notes (PDF/TXT) into short podcast episodes using AI summarization and Kokoro TTS.
Auth (register/login), upload, generate, and listen.

## Stack
- Frontend: Next.js (App Router, TypeScript) — login/register, dashboard, upload, episode list, player.
- Backend: FastAPI (Python) — JWT auth, file upload, summarization, Kokoro TTS integration.
- Storage: local `./server/data` (uploads + audio) for MVP.
- DB: SQLite (`./server/app.db`) via SQLModel.

## Quick Start (Dev)
### 1) Backend
```bash
cd server
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# (Optional) Install Kokoro from source if not already included by pip:
# pip install git+https://github.com/hexgrad/kokoro
cp .env.example .env  # edit secrets if desired
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend
```bash
cd app
pnpm i || npm i || yarn
cp .env.example .env.local  # set NEXT_PUBLIC_API_BASE (default http://localhost:8000)
pnpm dev || npm run dev || yarn dev
```

Open http://localhost:3000

## Kokoro voices
Kokoro ships voices as .pt files; this MVP uses the built-in voice names.
- Choose language in backend env (`KOKORO_LANG_CODE=e (es) | p (pt-BR) | a (en)`).
- Change default voice in `.env` / UI selector.
- If Kokoro isn't installed, the backend falls back to a basic pyttsx3 TTS (English) so you can test the pipeline.

## Endpoints (Backend)
- POST `/auth/register` {email, password}
- POST `/auth/login` {email, password} → {access_token}
- GET  `/voices` → list of voices
- POST `/uploads` (multipart: file) → {upload_id}
- POST `/process` {upload_id, target_minutes, style, voice} → {episode_id}
- GET  `/episodes` → [{id, title, status, duration_sec}]
- GET  `/episodes/{id}/audio` → audio file stream

## Notes
- Summarization uses a compact local LLM-free approach (TextRank + heuristics) for MVP stability; swap with your preferred LLM by replacing `summarize.py` (`summarize_llm` hook).
- PDFs are extracted with PyMuPDF; scanned PDFs will need OCR (Tesseract) — left as TODO with hook.

## Security
- JWT HS256; for production rotate `JWT_SECRET` and move to a real DB and object storage.
- CORS is open to `http://localhost:3000` by default.

Enjoy!
