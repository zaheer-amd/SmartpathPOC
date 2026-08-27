import json
from knowledge.loader import get_csd_policy

def evaluate_assessment(model, eligible_amount: float, oop_amount: float, decision: str, claim_type: str = "Vision (Glasses)", receipt_total: float = 250.0) -> dict:
    """
    Evaluates trainee submission against the active knowledge layer policy rules.
    """
    policy_content = get_csd_policy()
    
    judge_prompt = f"""
You are the SmartPath Assessment Evaluator.

--- KNOWLEDGE BASE: POLICY RULES ---
{policy_content}
--- END POLICY RULES ---

CURRENT CLAIM SCENARIO:
- Claim Type: {claim_type}
- Receipt Total: ${receipt_total:.2f}

TRAINEE SUBMISSION:
- Trainee Eligible Amount: ${eligible_amount:.2f}
- Trainee Out-of-Pocket Amount: ${oop_amount:.2f}
- Trainee Adjudication Decision: {decision}

TASK:
1. Refer strictly to the KNOWLEDGE BASE policy rules to determine the correct Eligible Amount, Out-of-Pocket Amount, and Decision for a ${receipt_total:.2f} claim.
2. Compare the trainee's submission against the policy rules.
3. If all values are correct, Status is "Pass" and Score is 100. Otherwise, Status is "Fail" and Score is 0.
4. Return ONLY a valid JSON object without markdown fences, matching this structure:
{{
    "Status": "Pass" or "Fail",
    "Score": 100 or 0,
    "Feedback": "One to two sentences explaining what was correct or what was calculated incorrectly based on the policy knowledge."
}}
"""
    
    response = model.generate_content(judge_prompt)
    clean_json = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)
