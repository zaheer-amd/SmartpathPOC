import json
from knowledge.loader import get_policy_by_plan

def get_mentor_response(model, user_question: str, plan_class: str, scenario: dict) -> dict:
    """
    Provides context-aware help based on the active policy.
    """
    policy_content = get_policy_by_plan(plan_class)
    
    mentor_prompt = f"""
You are the SmartPath Trainee Mentor, a helpful assistant for a claims adjudicator.

--- KNOWLEDGE BASE: ACTIVE POLICY RULES ---
{policy_content}
--- END POLICY RULES ---

CURRENT CLAIM SCENARIO:
- Plan Class: {plan_class}
- Scenario Details:
{json.dumps(scenario, indent=2)}

TRAINEE QUESTION:
{user_question}

INSTRUCTIONS:
1. Answer the trainee's question using ONLY the provided Knowledge Base rules.
2. Do not invent any rules, limits, or codes that are not explicitly stated above.
3. If the trainee asks about a scenario or service not covered by the active policy, politely inform them that you only have access to the rules for the {plan_class} plan.
4. Be encouraging but professional.
5. Keep your answer under 3 sentences.
6. IMPORTANT: Do NOT provide the exact Eligible Amount, Out-of-Pocket Amount, or Decision for the current scenario. Your goal is to guide the trainee to find the answer themselves.
"""
    
    response = model.generate_content(mentor_prompt)
    usage = response.usage_metadata
    return {
        "text": response.text,
        "telemetry": {
            "prompt_tokens": usage.prompt_token_count,
            "completion_tokens": usage.candidates_token_count,
            "total_tokens": usage.total_token_count
        }
    }
