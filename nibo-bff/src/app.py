import os
import time
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

NIBO_BASE_URL = (os.getenv("NIBO_BASE_URL") or "https://api.nibo.com.br").rstrip("/")
NIBO_APITOKEN = (os.getenv("NIBO_APITOKEN") or "").strip()
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT") or "20")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS") or "20")

if not NIBO_APITOKEN:
    print("[WARN] NIBO_APITOKEN não definido no .env")

app = FastAPI(title="nibo-bff", version="1.0.0")

# CORS (ajuste origins depois)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# cache simples em memória (opcional)
_cache: Dict[str, Any] = {"exp": 0, "data": None}

def _nibo_headers() -> Dict[str, str]:
    # Nibo usa ApiToken no header (não Authorization)
    return {
        "ApiToken": NIBO_APITOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

@app.get("/health")
def health():
    return {"ok": True, "service": "nibo-bff", "time": time.strftime("%Y-%m-%dT%H:%M:%S")}

@app.get("/accounts")
async def list_accounts(request: Request):
    """
    BFF para listar contas do Nibo.
    Repassa querystring (inclui OData: $top, $skip, $filter, $orderby etc.) para o Nibo.
    """
    # Se não tiver querystring, pode usar cache (evita bater no Nibo em cada reload)
    use_cache = len(request.query_params) == 0
    now = time.time()

    if use_cache and _cache["data"] is not None and _cache["exp"] > now:
        return {"source": "cache", **_cache["data"]}

    url = f"{NIBO_BASE_URL}/empresas/v1/accounts"

    # repassa query params exatamente (incluindo $top, $skip, etc.)
    params = dict(request.query_params)

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.get(url, headers=_nibo_headers(), params=params)

        # se der erro, devolve com detalhes p/ debug
        if r.status_code >= 400:
            raise HTTPException(
                status_code=r.status_code,
                detail={
                    "error": "NIBO_ACCOUNTS_FETCH_FAILED",
                    "status": r.status_code,
                    "body": _safe_json(r),
                },
            )

        data = _safe_json(r)
        payload = {"status": r.status_code, "data": data}

        if use_cache:
            _cache["data"] = payload
            _cache["exp"] = now + CACHE_TTL_SECONDS

        return {"source": "nibo", **payload}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail={"error": "TIMEOUT", "message": "Nibo timeout"})
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail={"error": "BAD_GATEWAY", "message": str(e)})

def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"text": response.text}