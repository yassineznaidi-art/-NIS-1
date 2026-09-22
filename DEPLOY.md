# Deploy NIS App v0.1 — Persistent HTTPS

This deploys **exactly the same code** you tested (no NIS Core redesign).

## One-click: Render (recommended, free, persistent)

**Prereq:** GitHub account (free) + Render account (free, same GitHub login).

1. Push to GitHub
```bash
cd /home/user/nis-mvv
git init
git add .
git commit -m "NIS App v0.1 — production ready"
gh repo create nis-app-v01 --public --source=. --push
# or: create repo on github.com manually, then:
# git remote add origin https://github.com/YOU/nis-app-v01.git
# git push -u origin main
```

2. Render
- Go to https://dashboard.render.com → New → Web Service → Connect `nis-app-v01`
- Render auto-detects `render.yaml` — keep defaults
- Add env vars (Dashboard → Environment):
  - `MODEL_PROVIDER=nis_core`
  - `NIS_USE_DENSE=false`
  - `NIS_DEBUG=false`
  - `OPENAI_API_KEY=` (leave empty or add if you later use OpenAI provider — server-only, never frontend)
- Deploy → wait 3-5 min → you get `https://nis-app-v01.onrender.com`

3. Verify (external, no token)
```bash
curl https://nis-app-v01.onrender.com/api/health
# {"status":"ok","provider":{"status":"ok"},"app":"nis-app-v0.1"}

curl -X POST https://nis-app-v01.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
# {"message":"[warm tone]...","deliberation_level":"L0"}

# Open on iPhone Safari: https://nis-app-v01.onrender.com
```

**Redeploy/update later:**
```bash
# change code, then:
git add -A && git commit -m "update NIS" && git push
# Render auto-redeploys. Or click Manual Deploy → Deploy latest commit.
```

## Alternative: Fly.io
```bash
fly launch   # creates fly.toml from Dockerfile
fly deploy
# you get https://nis-app-v01.fly.dev
# update: fly deploy
```

## Alternative: Railway / Vercel
Same repo, connect via their dashboard, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

## Local verification before deploy (already passing)
```bash
python run_arch_tests.py        # 6/6
python run_intelligence_tests.py # 12/12
python test_v03_p1.py           # 16/16
python tests_app/test_app.py    # 10/10
curl http://localhost:8000/api/health
```

## Secrets
Never put `OPENAI_API_KEY` in `frontend/` or `api/config` public response. Only as Render env var → available as `os.getenv("OPENAI_API_KEY")` server-side in `model_providers/`.

