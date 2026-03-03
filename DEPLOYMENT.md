# Deployment Guide (Free Stack)

This project is set up for:
- Frontend: Vercel Hobby
- Backend API: Render Free Web Service
- Database: Supabase Free Postgres

## 1) Supabase (Database)

1. Create a Supabase project.
2. Copy the Postgres connection string.
3. Convert it to asyncpg format for backend:
   - `postgresql://...` -> `postgresql+asyncpg://...`

Use this as `DATABASE_URL` in Render backend env vars.

## 2) Render (Backend API)

1. In Render, create a new **Web Service** from this GitHub repo.
2. Use:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add env vars:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `GROQ_API_KEY`
   - `GROQ_MODEL` (optional)
   - `SERPER_API_KEY` (optional but recommended)
   - `FRONTEND_URL` = your Vercel URL, e.g. `https://your-app.vercel.app`
   - `CORS_ORIGINS` = comma-separated allowed origins
     - Example: `https://your-app.vercel.app,http://localhost:3000`
   - `COOKIE_SECURE` = `true`
   - `COOKIE_SAMESITE` = `none`
   - `COOKIE_DOMAIN` = leave empty unless using custom shared domain
   - Optional: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ONESIGNAL_APP_ID`, `ONESIGNAL_REST_API_KEY`, `RESEND_API_KEY`
4. Deploy and verify:
   - `https://<your-render-service>.onrender.com/health`

The included `render.yaml` can be used for Blueprint-based setup.

## 3) Vercel (Frontend)

1. In Vercel, import this GitHub repo.
2. Configure:
   - Root Directory: `frontend`
   - Framework Preset: Next.js
3. Add env vars:
   - `NEXT_PUBLIC_API_URL` = your Render backend URL
   - Optional: `NEXT_PUBLIC_ONESIGNAL_APP_ID`
4. Deploy.

## 4) Google OAuth (if enabled)

In Google Cloud Console OAuth client settings, add:
- Authorized JavaScript origin: your frontend URL
- Authorized redirect URI: `https://<your-render-service>.onrender.com/auth/google/callback`

## 5) First Run Checklist

- Register user via frontend.
- Confirm `Set-Cookie` is present on login response.
- Confirm `/auth/me` succeeds from frontend (cookie included).
- Test chat and one CRUD flow (goals/budgets/loans).

## Notes about free tier

- Render free web service spins down after ~15 minutes idle (cold starts).
- Supabase free tier has usage/storage limits.
- Vercel Hobby has usage limits.
