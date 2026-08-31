import json
from knowledge.loader import get_policy_by_plan

def evaluate_assessment(model, eligible_amount: float, oop_amount: float, decision: str, plan_class: str) -> dict:
    """
    Evaluates trainee submission against the active knowledge layer policy rules.
    """
    policy_content = get_policy_by_plan(plan_class)
    
    judge_prompt = f"""
You are the SmartPath Assessment Evaluator.

--- KNOWLEDGE BASE: POLICY RULES ---
{policy_content}
--- END POLICY RULES ---

CURRENT CLAIM SCENARIO:
- Plan Class: {plan_class}

TRAINEE SUBMISSION:
- Trainee Eligible Amount: ${eligible_amount:.2f}
- Trainee Out-of-Pocket Amount: ${oop_amount:.2f}
- Trainee Adjudication Decision: {decision}

TASK:
1. Refer strictly to the KNOWLEDGE BASE policy rules to determine the correct Eligible Amount, Out-of-Pocket Amount, and Decision for the current claim.
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
    result_dict = json.loads(clean_json)
    
    usage = response.usage_metadata
    return {
        "assessment": result_dict,
        "telemetry": {
            "prompt_tokens": usage.prompt_token_count,
            "completion_tokens": usage.candidates_token_count,
            "total_tokens": usage.total_token_count
        }
    }
