from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("ASH_BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("ASH_BACKEND_PORT", "8000")),
        log_level="info",
    )
