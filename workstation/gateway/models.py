"""
Pydantic Request & Response Models for SmartPath AI Gateway
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ClaimRequest(BaseModel):
    api_key: str = Field(..., description="Gemini API Key")
    plan_class: str = Field(..., description="Insurance plan classification (e.g. Vision CSD-N, Dental PPO)")
    eligible_amount: float = Field(..., description="Adjudicated eligible coverage amount")
    oop_amount: float = Field(..., description="Calculated out-of-pocket amount")
    decision: str = Field(..., description="Adjudication decision (Approve/Deny)")
    model: Optional[str] = Field("gemini-flash-lite-latest", description="Gemini model identifier")
    scenario: dict[str, Any] = Field(..., description="Claim scenario metadata and invoice ledger")


class ChatRequest(BaseModel):
    api_key: str = Field(..., description="Gemini API Key")
    plan_class: str = Field(..., description="Insurance plan classification")
    message: str = Field(..., description="Trainee query to mentor agent")
    model: Optional[str] = Field("gemini-flash-lite-latest", description="Gemini model identifier")
    scenario: dict[str, Any] = Field(..., description="Claim scenario metadata and invoice ledger")


class SearchRequest(BaseModel):
    plan_class: str = Field(..., description="Insurance plan classification")
    query: str = Field(..., description="Semantic or keyword query against policy base")
    top_k: int = Field(2, description="Maximum number of policy sections to return")


class GenericResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[Any] = None
    telemetry: Optional[dict[str, Any]] = None
