from knowledge.loader import get_csd_policy

def get_mentor_response(model, user_question: str, claim_type: str = "Vision (Glasses)", receipt_total: float = 250.0) -> str:
    """
    Generates a mentoring response based on questions and grounded in the knowledge layer policy.
    """
    policy_content = get_csd_policy()
    
    mentor_prompt = f"""
You are the SmartPath Live Assistant guiding a trainee claims adjudicator.

--- KNOWLEDGE BASE: POLICY RULES ---
{policy_content}
--- END POLICY RULES ---

CURRENT CLAIM SCENARIO:
- Claim Type: {claim_type}
- Receipt Total: ${receipt_total:.2f}

TRAINEE QUESTION:
"{user_question}"

INSTRUCTIONS:
1. Answer the trainee's question politely and concisely.
2. Base all explanations and guidance strictly on the KNOWLEDGE BASE policy rules.
3. Provide hints and guiding logic (e.g. how policy limits or out-of-pocket rules work).
4. DO NOT directly give away the exact final calculation or answers.
5. Keep your answer under 3 sentences.
"""
    
    return model.generate_content(mentor_prompt).text
