from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import os
from agents.mentor_agent import get_mentor_response

app = FastAPI()

# In a real app, this comes from os.getenv("GEMINI_API_KEY")
# For the POC, we will allow Akka to pass the key via the API request for simplicity
class ClaimRequest(BaseModel):
    api_key: str
    eligible_amount: float
    oop_amount: float
    decision: str

class ChatRequest(BaseModel):
    api_key: str
    message: str

@app.post("/evaluate")
def evaluate_claim(request: ClaimRequest):
    try:
        # Configure the model using the key passed from the frontend -> Akka -> Here
        genai.configure(api_key=request.api_key)
        model = genai.GenerativeModel('gemini-3.6-flash')
        
        # The prompt from your judge_agent
        prompt = f"""
        You are the SmartPath Assessment Evaluator.
        The policy is CSD N. The claim is for $250. The coverage limit is $200.
        The correct eligible amount is $200. The correct out-of-pocket amount is $50.
        The correct decision is Approve.
        
        The trainee submitted:
        - Eligible: ${request.eligible_amount}
        - Out-of-Pocket: ${request.oop_amount}
        - Decision: {request.decision}
        
        Evaluate this strictly against the rules. Return ONLY a valid JSON object exactly like this:
        {{
            "Status": "Pass" or "Fail",
            "Score": 100 or 0,
            "Feedback": "One sentence explaining what they did right or wrong."
        }}
        """
        
        response = model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        
        return {"success": True, "data": clean_json}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/chat")
def chat_assistant(request: ChatRequest):
    try:
        genai.configure(api_key=request.api_key)
        model = genai.GenerativeModel('gemini-3.6-flash')
        response_text = get_mentor_response(model, request.message)
        return {"success": True, "data": response_text}
    except Exception as e:
        return {"success": False, "error": str(e)}