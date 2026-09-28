"""
SaaSCommand 360 - Main FastAPI Application Entrypoint
Conforms to Section 12 & Section 16 of the Capstone Brief:
- Auto-generated OpenAPI / Swagger docs at /docs
- CORS middleware for React / Vite frontend
- Request validation, logging, and exception handlers
"""

import os
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.api.routes import router as api_router

app = FastAPI(
    title="SaaSCommand 360 API",
    description="Enterprise SaaS Product, Revenue & Customer Success Analytics Command Center REST Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for performance logging & latency headers
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "message": str(exc)}
    )

# Include API Router
app.include_router(api_router)

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "ONLINE",
        "service": "SaaSCommand 360 REST Engine",
        "version": "1.0.0",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
