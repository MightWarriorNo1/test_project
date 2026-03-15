# NTL Detection Engine — React UI

Dashboard for the NTL Detection API: health check, inference request form, and results (flagged meters with reason codes).

## Local development

1. Install and run the API (from project root):
   ```bash
   uvicorn ntl_engine.api.app:create_app --factory --host 0.0.0.0 --port 8000
   ```

2. From `frontend/`:
   ```bash
   npm install
   npm run dev
   ```
   Open http://localhost:3000. The app proxies `/api` to `http://localhost:8000`.

## Build

```bash
npm run build
```
Output is in `dist/`.

## Deploy on Vercel (UI only)

The **React app** can be hosted on Vercel. The **FastAPI backend** cannot run as a long-lived server on Vercel; host it elsewhere (e.g. Railway, Render, Fly.io, or your own server).

### Steps

1. Push the repo to GitHub (include the `frontend/` folder).

2. In [Vercel](https://vercel.com), import the project and set:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`

3. Add an environment variable so the UI calls your API:
   - **Name:** `VITE_API_URL`
   - **Value:** your API base URL (e.g. `https://your-api.onrender.com` or `https://ntl-api.fly.dev`)
   Do not add a trailing slash.

4. Deploy. The UI will be served from a `*.vercel.app` URL and will call your API at `VITE_API_URL`.

### CORS

The FastAPI app allows all origins (`allow_origins=["*"]`). For production you may want to restrict this to your Vercel domain(s).
