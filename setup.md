# FinSight News Setup and Run Commands

This file contains commands to run the FinSight News module.

## 1) Prerequisites

- Python 3.11+
- Docker Desktop (optional, for containerized run)
- A configured `.env` file in this folder (`finsight-news/.env`)

## 2) Run with Docker (recommended)

From `finsight-news` folder:

```powershell
docker-compose build
docker-compose up -d
```

Check services:

```powershell
docker-compose ps
```

Stop services:

```powershell
docker-compose down
```

## 3) Run locally (PowerShell)

From repo root (`FinSight`):

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
cd .\finsight-news
pip install -r requirements.txt
```

Start API server:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open a new terminal (same folder, venv activated) and start Celery worker:

```powershell
celery -A celery_app worker --loglevel=info -P solo
```

Open another terminal and start Celery beat scheduler:

```powershell
celery -A celery_app beat --loglevel=info
```

## 4) Verify

- API docs: http://localhost:8000/docs
- Health endpoint: http://localhost:8000/health
