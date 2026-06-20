#!/usr/bin/env python3
"""Server dashboard + API — accessibile da LAN, non usa il touchscreen."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    import uvicorn
    from server.app.config import SERVER_HOST, SERVER_PORT

    uvicorn.run("server.app.main:app", host=SERVER_HOST, port=SERVER_PORT, log_level="info")
