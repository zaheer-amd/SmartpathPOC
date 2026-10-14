import os
import requests
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent
RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8000")

def load_policy(filename: str) -> str:
    """Legacy direct file loading (fallback)."""
    policy_path = KNOWLEDGE_DIR / "policies" / filename
    if not policy_path.exists():
        policy_path = KNOWLEDGE_DIR / filename
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found at: {policy_path}")
    
    with open(policy_path, "r", encoding="utf-8") as f:
        return f.read()

def get_policy_by_plan(plan_class: str) -> dict:
    """
    Retrieves policy content via the mock RAG search endpoint.
    Returns a dict with 'content' and 'retrieval_source' keys.
    
    Falls back to direct file reading if the RAG service is unreachable.
    """
    try:
        response = requests.post(
            f"{RAG_SERVICE_URL}/search",
            json={"plan_class": plan_class, "query": "adjudication rules coverage limits eligible amount", "top_k": 3},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # Concatenate all returned sections into a single context string
            combined_content = "\n\n".join(r["content"] for r in data.get("results", []))
            return {
                "content": combined_content,
                "retrieval_source": "mock-azure-ai-search"
            }
    except requests.exceptions.RequestException:
        pass  # Fall through to direct file reading
    
    # Fallback: direct file reading (backward compatible)
    plan_lower = plan_class.lower()
    if "vision" in plan_lower or "csd n" in plan_lower:
        filename = "CSD_policy.md"
    elif "dental" in plan_lower:
        filename = "dental_ppo.md"
    elif "pharmacy" in plan_lower or "rx" in plan_lower:
        filename = "pharmacy_rx.md"
    else:
        filename = "CSD_policy.md"
        
    return {
        "content": load_policy(filename),
        "retrieval_source": "local-file-fallback"
    }

def get_csd_policy() -> str:
    """Convenience getter for CSD-N policy (Legacy compatibility)."""
    return load_policy("CSD_policy.md")
