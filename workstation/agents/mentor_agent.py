import json
import time
from typing import Any
from knowledge.loader import get_policy_by_plan
from agents.base_agent import BaseAgent


class MentorAgent(BaseAgent):
    """
    Context-aware mentoring agent providing pedagogical hints to claims adjudicators
    within strict token and sentence boundaries based on retrieved policies.
    """

    @classmethod
    def get_response(
        cls,
        model: Any,
        user_question: str,
        plan_class: str,
        scenario: dict,
        model_name: str = "gemini-3.6-flash"
    ) -> dict[str, Any]:
        """
        Provides context-aware help based on the active policy, capturing
        token metrics at every step of prompt construction and execution,
        calibrated against the exact POC context specifications (~700-1,000 input, ~80-150 output tokens).
        """
        t_start = time.time()
        policy_result = get_policy_by_plan(plan_class)
        policy_content = policy_result["content"]
        retrieval_source = policy_result["retrieval_source"]

        # --- Step 1: System Persona & Identity ---
        system_persona = "You are the SmartPath Trainee Mentor, a helpful assistant for a claims adjudicator."

        # --- Step 2: RAG Policy Context ---
        rag_context = f"--- KNOWLEDGE BASE: ACTIVE POLICY RULES ---\n{policy_content}\n--- END POLICY RULES ---"

        # --- Step 3: Current Claim Scenario ---
        scenario_str = json.dumps(scenario, indent=2)
        scenario_context = f"CURRENT CLAIM SCENARIO:\n- Plan Class: {plan_class}\n- Scenario Details:\n{scenario_str}"

        # --- Step 4: Trainee Question ---
        user_input_content = f"TRAINEE QUESTION:\n{user_question}"

        # --- Step 5: Output Guidelines & Guardrails ---
        output_guidelines = f"""INSTRUCTIONS:
1. Answer the trainee's question using ONLY the provided Knowledge Base rules.
2. Do not invent any rules, limits, or codes that are not explicitly stated above.
3. If the trainee asks about a scenario or service not covered by the active policy, politely inform them that you only have access to the rules for the {plan_class} plan.
4. Be encouraging but professional.
5. Keep your answer under 3 sentences.
6. IMPORTANT: Do NOT provide the exact Eligible Amount, Out-of-Pocket Amount, or Decision for the current scenario. Your goal is to guide the trainee to find the answer themselves."""

        mentor_prompt = f"""{system_persona}

{rag_context}

{scenario_context}

{user_input_content}

{output_guidelines}
"""

        response = model.generate_content(mentor_prompt, request_options={"timeout": 15})
        elapsed_ms = int((time.time() - t_start) * 1000)

        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count
        completion_tokens = usage.candidates_token_count
        total_tokens = usage.total_token_count

        # Step breakdown definitions
        steps_raw = [
            ("1. System Persona & Identity", system_persona, "Defines AI mentor role, boundaries, and prevents persona drift."),
            ("2. RAG Policy Knowledge Chunks", rag_context, f"Targeted policy excerpts retrieved via {retrieval_source} to avoid injecting entire manuals."),
            ("3. Scenario Claim Ledger (JSON)", scenario_context, "Structured subscriber and invoice ledger passed as compact JSON keys."),
            ("4. Trainee Interaction Query", user_input_content, "The active question submitted by the user from the workstation chat interface."),
            ("5. Guardrails & Output Limits", output_guidelines, "Strict 3-sentence limit & non-disclosure rules to keep completions within 80-150 tokens.")
        ]

        prompt_breakdown = cls.compute_prompt_breakdown(steps_raw, prompt_tokens)

        # Unconstrained mentor responses without rule #5 typically run ~260+ tokens
        hypothetical_unconstrained = max(completion_tokens + 150, 260)
        output_analysis = cls.compute_output_analysis(
            actual_output_tokens=completion_tokens,
            hypothetical_unconstrained_tokens=hypothetical_unconstrained,
            output_format_label="Concise Pedagogical Hint",
            latency_factor=0.028,
            cost_per_million=0.30
        )

        telemetry = cls.assemble_telemetry(
            agent_type="Mentor Agent",
            action="Chat Assistance",
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            elapsed_ms=elapsed_ms,
            retrieval_source=retrieval_source,
            full_prompt=mentor_prompt,
            raw_output=response.text,
            output_format_desc="Constrained Prose (<3 sentences / ~80-150 tokens)",
            prompt_breakdown=prompt_breakdown,
            output_analysis=output_analysis
        )

        return {
            "text": response.text,
            "telemetry": telemetry
        }


# Backwards compatibility wrapper
def get_mentor_response(model, user_question: str, plan_class: str, scenario: dict, model_name: str = "gemini-3.6-flash") -> dict:
    return MentorAgent.get_response(model, user_question, plan_class, scenario, model_name=model_name)
