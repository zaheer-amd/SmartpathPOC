"""
FastAPI Route: /search and /policy/{plan_class} (Mock Azure AI Search & Policy Retrieval)
"""

from fastapi import APIRouter
from gateway.models import SearchRequest
from knowledge.policy_index import search_policy, get_full_policy

router = APIRouter()


@router.post("/search")
def search_knowledge(request: SearchRequest):
    """Mock Azure AI Search — returns relevant policy sections."""
    results = search_policy(request.plan_class, request.query, request.top_k)
    return {
        "success": True,
        "source": "mock-azure-ai-search",
        "results": results
    }


@router.get("/policy/{plan_class}")
def get_policy(plan_class: str):
    """Returns the full policy document for a plan class."""
    content = get_full_policy(plan_class)
    return {
        "success": True,
        "source": "mock-azure-ai-search",
        "content": content
    }
