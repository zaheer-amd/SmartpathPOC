import json
import time
from typing import Any
from knowledge.loader import get_policy_by_plan
from agents.base_agent import BaseAgent


class JudgeAgent(BaseAgent):
    """
    Assessment evaluator comparing trainee adjudication submissions against
    active policy rules, capturing layer-by-layer prompt telemetry and
    demonstrating structured JSON output token efficiencies.
    """

    @classmethod
    def evaluate(
        cls,
        model: Any,
        eligible_amount: float,
        oop_amount: float,
        decision: str,
        plan_class: str,
        scenario: dict,
        model_name: str = "gemini-3.6-flash"
    ) -> dict[str, Any]:
        """
        Evaluates trainee submission against the active knowledge layer policy rules,
        capturing token counts at every step and measuring JSON efficiency savings,
        calibrated against the exact POC context specifications (~800-1,200 input, ~50-100 output tokens).
        """
        t_start = time.time()
        policy_result = get_policy_by_plan(plan_class)
        policy_content = policy_result["content"]
        retrieval_source = policy_result["retrieval_source"]

        # --- Step 1: System Persona & Identity ---
        system_persona = "You are the SmartPath Assessment Evaluator."

        # --- Step 2: RAG Policy Context ---
        rag_context = f"--- KNOWLEDGE BASE: POLICY RULES ---\n{policy_content}\n--- END POLICY RULES ---"

        # --- Step 3: Current Claim Scenario ---
        scenario_str = json.dumps(scenario, indent=2)
        scenario_context = f"CURRENT CLAIM SCENARIO:\n- Plan Class: {plan_class}\n- Scenario Details:\n{scenario_str}"

        # --- Step 4: Trainee Submission Values ---
        user_input_content = f"""TRAINEE SUBMISSION:
- Trainee Eligible Amount: ${eligible_amount:.2f}
- Trainee Out-of-Pocket Amount: ${oop_amount:.2f}
- Trainee Adjudication Decision: {decision}"""

        # --- Step 5: Task Instructions & Strict JSON Schema ---
        task_schema = """TASK:
1. Refer strictly to the KNOWLEDGE BASE policy rules to determine the correct Eligible Amount, Out-of-Pocket Amount, and Decision for the current claim.
2. Compare the trainee's submission against the policy rules.
3. If all values are correct, Status is "Pass" and Score is 100. Otherwise, Status is "Fail" and Score is 0.
4. IMPORTANT: Do NOT reveal the exact correct amounts or the final expected answers in your feedback. Simply explain what part of the policy rule they applied incorrectly or need to review.
5. Return ONLY a valid JSON object without markdown fences, matching this structure:
{
    "Status": "Pass" or "Fail",
    "Score": 100 or 0,
    "Feedback": "One to two sentences explaining what was correct or what was calculated incorrectly based on the policy knowledge."
}"""

        judge_prompt = f"""{system_persona}

{rag_context}

{scenario_context}

{user_input_content}

{task_schema}
"""

        response = model.generate_content(judge_prompt, request_options={"timeout": 15})
        elapsed_ms = int((time.time() - t_start) * 1000)

        raw_text = response.text
        clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        try:
            result_dict = json.loads(clean_json)
        except Exception:
            result_dict = {"Status": "Fail", "Score": 0, "Feedback": clean_json}

        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count
        completion_tokens = usage.candidates_token_count
        total_tokens = usage.total_token_count

        # Step breakdown definitions
        steps_raw = [
            ("1. System Persona & Identity", system_persona, "Establishes unbiased adjudicator audit role and objective standards."),
            ("2. RAG Policy Knowledge Chunks", rag_context, f"Top-K policy rules injected from {retrieval_source} covering {plan_class} limits."),
            ("3. Scenario Claim Ledger (JSON)", scenario_context, "Full subscriber eligibility and line-item invoice data in structured JSON."),
            ("4. Trainee Submission Inputs", user_input_content, "Candidate's adjudication calculations (eligible $, OOP $, decision code)."),
            ("5. Output Contract & JSON Schema", task_schema, "Strict schema specification forcing the LLM into compact, deterministic JSON output (~50-100 tokens).")
        ]

        prompt_breakdown = cls.compute_prompt_breakdown(steps_raw, prompt_tokens)

        # Free-text evaluation narrative without schema constraints benchmark (~280+ tokens)
        hypothetical_freetext = max(completion_tokens + 210, 280)
        output_analysis = cls.compute_output_analysis(
            actual_output_tokens=completion_tokens,
            hypothetical_unconstrained_tokens=hypothetical_freetext,
            output_format_label="Structured JSON Object",
            latency_factor=0.032,
            cost_per_million=0.30
        )

        telemetry = cls.assemble_telemetry(
            agent_type="Judge Agent",
            action="Assessment Evaluation",
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            elapsed_ms=elapsed_ms,
            retrieval_source=retrieval_source,
            full_prompt=judge_prompt,
            raw_output=raw_text,
            output_format_desc="Strict JSON Schema (~50-100 tokens)",
            prompt_breakdown=prompt_breakdown,
            output_analysis=output_analysis,
            extra={"parsed_json": result_dict}
        )

        return {
            "assessment": result_dict,
            "telemetry": telemetry
        }


# Backwards compatibility wrapper
def evaluate_assessment(model, eligible_amount: float, oop_amount: float, decision: str, plan_class: str, scenario: dict, model_name: str = "gemini-3.6-flash") -> dict:
    return JudgeAgent.evaluate(model, eligible_amount, oop_amount, decision, plan_class, scenario, model_name=model_name)
