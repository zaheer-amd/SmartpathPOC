"""
SmartPath Base Agent Infrastructure

Provides shared telemetry, token-breakdown accounting, prompt layering analysis,
and cost/latency savings estimation for all workstation agents.
"""

from typing import Any, Optional


class BaseAgent:
    """Base class for SmartPath agents providing shared telemetry capabilities."""

    @staticmethod
    def compute_prompt_breakdown(
        steps_raw: list[tuple[str, str, str]],
        prompt_tokens: int
    ) -> list[dict[str, Any]]:
        """
        Calculates character-proportional token breakdown across prompt layers
        calibrated to match Gemini's actual prompt token count.

        Args:
            steps_raw: List of (step_title, content_string, why_description) tuples.
            prompt_tokens: Ground-truth prompt token count from model usage metadata.

        Returns:
            List of step telemetry dictionaries.
        """
        total_char_len = sum(len(content) for _, content, _ in steps_raw) or 1
        prompt_breakdown: list[dict[str, Any]] = []
        accumulated_tokens = 0

        for idx, (step_title, content, why_desc) in enumerate(steps_raw):
            if idx == len(steps_raw) - 1:
                step_tokens = max(1, prompt_tokens - accumulated_tokens)
            else:
                step_tokens = max(1, round(prompt_tokens * (len(content) / total_char_len)))
                accumulated_tokens += step_tokens

            pct = round((step_tokens / prompt_tokens) * 100, 1) if prompt_tokens > 0 else 0.0
            prompt_breakdown.append({
                "step_num": idx + 1,
                "title": step_title,
                "content": content,
                "tokens": step_tokens,
                "pct": pct,
                "char_count": len(content),
                "why": why_desc
            })

        return prompt_breakdown

    @staticmethod
    def compute_output_analysis(
        actual_output_tokens: int,
        hypothetical_unconstrained_tokens: int,
        output_format_label: str,
        latency_factor: float = 0.030,
        cost_per_million: float = 0.30
    ) -> dict[str, Any]:
        """
        Calculates token, latency, and cost savings compared to unconstrained generation.
        """
        tokens_saved = max(0, hypothetical_unconstrained_tokens - actual_output_tokens)
        pct_savings = (
            round((tokens_saved / hypothetical_unconstrained_tokens) * 100, 1)
            if hypothetical_unconstrained_tokens > 0 else 0.0
        )

        return {
            "output_format": output_format_label,
            "actual_output_tokens": actual_output_tokens,
            "hypothetical_unconstrained_tokens": hypothetical_unconstrained_tokens,
            "tokens_saved": tokens_saved,
            "pct_savings": pct_savings,
            "latency_savings_est_sec": round(tokens_saved * latency_factor, 2),
            "cost_savings_est_usd": round((tokens_saved / 1_000_000) * cost_per_million, 6)
        }

    @classmethod
    def assemble_telemetry(
        cls,
        agent_type: str,
        action: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        elapsed_ms: int,
        retrieval_source: str,
        full_prompt: str,
        raw_output: str,
        output_format_desc: str,
        prompt_breakdown: list[dict[str, Any]],
        output_analysis: dict[str, Any],
        extra: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Assembles the canonical telemetry payload dictionary."""
        telemetry: dict[str, Any] = {
            "agent_type": agent_type,
            "action": action,
            "model_name": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "agent_latency_ms": elapsed_ms,
            "round_trip_ms": elapsed_ms,
            "within_10s_limiter": elapsed_ms <= 10000,
            "retrieval_source": retrieval_source,
            "full_prompt": full_prompt,
            "raw_output": raw_output,
            "output_format": output_format_desc,
            "prompt_breakdown": prompt_breakdown,
            "output_analysis": output_analysis
        }
        if extra:
            telemetry.update(extra)
        return telemetry
