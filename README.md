# nibo-bff-account

BFF (Backend for Frontend) built with **Python + FastAPI** to list accounts from the Nibo API.

## Features
- Secure API token handling
- OData query passthrough
- Simple in-memory cache
- Ready for frontend consumption

## Endpoints
- `GET /health`
- `GET /accounts`

## Run locally
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app:app --reload
