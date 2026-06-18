from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

import config

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    if not config.API_KEY:
        return "dev"
    if not api_key or api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="API key non valida")
    return api_key
