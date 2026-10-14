"""
SmartPath AI Gateway Service

FastAPI gateway managing agent dispatch, mock Azure AI Search retrieval,
and policy document access over HTTP.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure workstation root is in sys.path
_workstation_root = str(Path(__file__).resolve().parent.parent)
if _workstation_root not in sys.path:
    sys.path.insert(0, _workstation_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from knowledge.policy_index import build_index
from gateway.routes.evaluate import router as evaluate_router
from gateway.routes.chat import router as chat_router
from gateway.routes.search import router as search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager replacing deprecated startup/shutdown events."""
    build_index()
    print("[RAG] Policy index built. Mock Azure AI Search ready on /search and /policy/")
    yield


app = FastAPI(
    title="SmartPath AI Gateway",
    description="Enterprise API Gateway orchestrating Judge & Mentor agents and RAG knowledge policies",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers
app.include_router(evaluate_router)
app.include_router(chat_router)
app.include_router(search_router)


@app.get("/health")
def health_check():
    """Health check endpoint for orchestrator and monitoring."""
    return {"status": "ok", "service": "smartpath-ai-gateway"}