"""
SmartPath Workstation Configuration

Centralized configuration for endpoints, ports, model defaults, and file paths.
Used by Streamlit UI and Gateway services to avoid hardcoding localhost strings.
"""

import os
from pathlib import Path

# Paths
WORKSTATION_ROOT = Path(__file__).resolve().parent
DATA_DIR = WORKSTATION_ROOT / "data"
SCENARIOS_FILE = DATA_DIR / "scenarios.json"
INVOICES_DIR = DATA_DIR / "invoices"

# Model Defaults
DEFAULT_MODEL = os.environ.get("SMARTPATH_DEFAULT_MODEL", "gemini-flash-lite-latest")
FALLBACK_MODEL = "gemini-3.6-flash"

# AI Gateway Service (FastAPI - Port 8000)
GATEWAY_HOST = os.environ.get("GATEWAY_HOST", "localhost")
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8000"))
GATEWAY_URL = os.environ.get("GATEWAY_URL", f"http://{GATEWAY_HOST}:{GATEWAY_PORT}")

# Akka Orchestrator Service (Scala - Port 8080)
ORCHESTRATOR_HOST = os.environ.get("ORCHESTRATOR_HOST", "localhost")
ORCHESTRATOR_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "8080"))
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL", f"http://{ORCHESTRATOR_HOST}:{ORCHESTRATOR_PORT}")

# Workstation UI Service (Streamlit - Port 8501)
WORKSTATION_PORT = int(os.environ.get("WORKSTATION_PORT", "8501"))

# Timeouts
REQUEST_TIMEOUT_SECONDS = 30
POLICY_TIMEOUT_SECONDS = 5
LLM_TIMEOUT_SECONDS = 15


# Helper URL Generators
def get_policy_url(plan_class: str) -> str:
    """Returns endpoint for fetching plan policy documentation."""
    return f"{GATEWAY_URL}/policy/{plan_class}"


def get_session_history_url(session_id: str) -> str:
    """Returns endpoint for fetching Akka SQLite session history."""
    return f"{ORCHESTRATOR_URL}/session/{session_id}/history"
