"""
FastAPI Route: /chat (Mentor Agent Assistance)
"""

import time
from fastapi import APIRouter
import google.generativeai as genai
from gateway.models import ChatRequest, GenericResponse
from agents.mentor_agent import get_mentor_response
from config import DEFAULT_MODEL

router = APIRouter()


@router.post("/chat", response_model=GenericResponse)
def chat_assistant(request: ChatRequest):
    t_start = time.time()
    try:
        genai.configure(api_key=request.api_key)
        model_name = request.model or DEFAULT_MODEL
        model = genai.GenerativeModel(model_name)

        result = get_mentor_response(
            model=model,
            user_question=request.message,
            plan_class=request.plan_class,
            scenario=request.scenario,
            model_name=model_name
        )
        elapsed_ms = int((time.time() - t_start) * 1000)
        telemetry = result.get("telemetry", {})
        telemetry["round_trip_ms"] = elapsed_ms
        telemetry["model_name"] = model_name
        telemetry["within_10s_limiter"] = elapsed_ms <= 10000

        return GenericResponse(
            success=True,
            data=result["text"],
            telemetry=telemetry
        )
    except Exception as e:
        return GenericResponse(
            success=False,
            error=str(e)
        )
