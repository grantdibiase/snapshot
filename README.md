# snapshot
AI-Powered college schedule reader that builds a Google Calendar from screenshots!

## Run locally

Backend:

```powershell
pip install -r backend/requirements.txt
$env:GOOGLE_CREDENTIALS_JSON = Get-Content .\credentials.json -Raw
uvicorn backend.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm start
```

The deployed API health check is `https://snapshot-backend-j49i.onrender.com/`.
It should return `{"status":"Snapshot API is running!"}`.

## Deploy the backend to Render

This repository includes `render.yaml`. In Render, choose **New > Blueprint** and connect this repository. If creating the service manually, use:

- Root directory: repository root
- Build command: `pip install -r backend/requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

Set these Render environment variables:

- `OPENAI_API_KEY`: the OpenAI API key used to read and parse screenshots. Store it as a secret. Without it the health endpoint still works, but uploads return HTTP 503.
- `GOOGLE_CREDENTIALS_JSON`: the complete contents of `credentials.json` as one JSON value. Add it as a secret; do not commit it.
- `FRONTEND_URL`: the exact deployed Vercel URL, without a trailing slash.
- `BACKEND_URL`: the exact Render service URL, without a trailing slash.

In Google Cloud Console, add `https://<your-render-service>.onrender.com/auth/callback` as an authorized redirect URI for the OAuth client. After deployment, open the Render `/` URL first to confirm the service is running, then test upload and Google Calendar connection from the frontend.

Render's default filesystem is temporary. The current app writes OAuth sessions to `sessions/`, so a restart or redeploy can invalidate existing sessions. That is acceptable for a demo, but production use should move session storage to a database or another durable store.

OAuth login state is held in memory for ten minutes. Keep the current single-worker configuration; a restart during Google login requires reconnecting. `SESSIONS_DIR` can point to a mounted persistent disk for completed sessions.

Free Render services sleep after 15 minutes without traffic and can take about a minute to wake. Choose a paid **service compute plan** to remove idle sleep; upgrading only the workspace plan does not remove it. Existing manually configured services must have the environment variables and health check (`/`) applied in the dashboard as well.

## Backend regression checks

```powershell
pip install -r backend/requirements.txt httpx
python -m unittest tests.test_backend -q
```

These tests mock screenshot processing and do not create Google Calendar events or call OpenAI. Uploads accept up to ten PNG/JPEG files, each at most 10 MB.

## Google consent screen and event review

The sign-in flow redirects to Google and restores the session in the same browser tab. Expired server sessions prompt reconnection. The Google unverified-app warning cannot be removed in frontend code: configure the correct project in Google Auth Platform, set branding/support details, add test users under Audience while testing, and complete the applicable verification before public launch. Keep the authorized redirect URI set to the Render `/auth/callback` URL. Do not publish placeholder privacy-policy or terms pages.

Recurring events require explicit semester dates. The parser leaves missing dates empty instead of guessing. Review the year before importing; these changes do not move existing 2024 calendar entries.

Event category definitions are shared in `frontend/src/eventTypes.json`: lecture (blue), lab (teal), recitation (purple), exam (red), assignment (yellow), office hours (green), other (gray). Google renders its own palette for the corresponding color IDs. Existing events retain their previous colors until edited.
