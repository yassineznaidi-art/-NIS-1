# NIS — نِيسْ — App v0.1

Calm intelligent assistant — shell around NIS Core (v1.1 + v0.2 + v0.3-P1).

**Live:** `https://nis-app-v01.onrender.com` (after deploy)

## Quick start
```bash
pip install -r requirements_v03.txt -r requirements_app.txt
python setup_memory.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

## Deploy (Render, persistent HTTPS)
See `DEPLOY.md` and `render.yaml` — one-click via dashboard.render.com.

## Tests
```bash
python run_arch_tests.py        # 6/6
python run_intelligence_tests.py # 12/12
python test_v03_p1.py           # 16/16
python tests_app/test_app.py    # 10/10
```

## Structure
- `nis/` — NIS Core (authority, no redesign)
- `app/` — adapter, sessions, config
- `model_providers/` — nis_core / mock
- `frontend/` — mobile-responsive UI

Docs: `NIS_APP_v0.1_REPORT.md`, `NIS_v0.3_P1_REPORT.md`
