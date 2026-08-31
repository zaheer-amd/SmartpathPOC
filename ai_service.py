from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai
import os
from agents.mentor_agent import get_mentor_response
from agents.judge_agent import evaluate_assessment

app = FastAPI()

DEFAULT_MODEL = "gemini-3.6-flash"

class ClaimRequest(BaseModel):
    api_key: str
    plan_class: str
    eligible_amount: float
    oop_amount: float
    decision: str
    model: Optional[str] = DEFAULT_MODEL

class ChatRequest(BaseModel):
    api_key: str
    plan_class: str
    message: str
    model: Optional[str] = DEFAULT_MODEL

@app.post("/evaluate")
def evaluate_claim(request: ClaimRequest):
    try:
        genai.configure(api_key=request.api_key)
        model_name = request.model or DEFAULT_MODEL
        model = genai.GenerativeModel(model_name)
        
        result = evaluate_assessment(model, request.eligible_amount, request.oop_amount, request.decision, request.plan_class)
        return {"success": True, "data": result["assessment"], "telemetry": result["telemetry"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/chat")
def chat_assistant(request: ChatRequest):
    try:
        genai.configure(api_key=request.api_key)
        model_name = request.model or DEFAULT_MODEL
        model = genai.GenerativeModel(model_name)
        
        result = get_mentor_response(model, request.message, request.plan_class)
        return {"success": True, "data": result["text"], "telemetry": result["telemetry"]}
    except Exception as e:
        return {"success": False, "error": str(e)}