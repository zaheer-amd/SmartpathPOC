"""
FastAPI Route: /evaluate (Judge Agent Assessment Evaluation)
"""

import time
from fastapi import APIRouter
import google.generativeai as genai
from gateway.models import ClaimRequest, GenericResponse
from agents.judge_agent import evaluate_assessment
from config import DEFAULT_MODEL

router = APIRouter()


@router.post("/evaluate", response_model=GenericResponse)
def evaluate_claim(request: ClaimRequest):
    t_start = time.time()
    try:
        genai.configure(api_key=request.api_key)
        model_name = request.model or DEFAULT_MODEL
        model = genai.GenerativeModel(model_name)

        result = evaluate_assessment(
            model=model,
            eligible_amount=request.eligible_amount,
            oop_amount=request.oop_amount,
            decision=request.decision,
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
            data=result["assessment"],
            telemetry=telemetry
        )
    except Exception as e:
        return GenericResponse(
            success=False,
            error=str(e)
        )
