"""
SmartPath Workstation Trainee Inputs Component

Renders the trainee work area:
1. Input fields for eligible amount, out-of-pocket amount, decision, EOB code
2. Submit button sending evaluation to Akka Orchestrator over HTTP
3. Real-time feedback, score, and token telemetry recording
"""

import time
from typing import Any
import streamlit as st
import requests
from config import ORCHESTRATOR_URL, REQUEST_TIMEOUT_SECONDS


def render_trainee_inputs(
    current_scenario: dict[str, Any],
    plan_class: str,
    api_key: str,
    selected_model: str
) -> None:
    """Renders trainee calculation fields and evaluation submission logic."""
    st.write("---")
    st.markdown("#### ✍️ Trainee Adjudication Work Area")

    inp_col1, inp_col2 = st.columns(2)
    with inp_col1:
        eligible_amount = st.number_input(
            "Enter Eligible Amount ($):",
            min_value=0.0,
            step=10.0,
            help="Amount covered by the insurance policy limit."
        )
        decision = st.selectbox(
            "Adjudication Decision:",
            ["Select...", "Approve", "Deny", "Manual Review"],
            help="Select Approve if calculation complies with policy, Deny if non-covered."
        )
    with inp_col2:
        oop_amount = st.number_input(
            "Enter Out-of-Pocket Amount ($):",
            min_value=0.0,
            step=10.0,
            help="Amount the patient must pay out of pocket (Receipt Total minus Eligible Amount)."
        )
        eob_code = st.selectbox(
            "EOB / Explanation Code:",
            [
                "Select code...",
                "E00 - Approved as Incurred",
                "E01 - Benefit Maximum Reached",
                "D04 - Exceeds Frequency Limit",
                "R09 - Missing Provider Prescription Details"
            ]
        )

    submit_button = st.button("Submit Assessment", type="primary")

    if submit_button:
        if decision == "Select...":
            st.error("Please select an Adjudication Decision.")
        else:
            with st.spinner("🤖 Sending assessment to Orchestrator..."):
                try:
                    payload = {
                        "api_key": api_key,
                        "plan_class": plan_class,
                        "eligible_amount": eligible_amount,
                        "oop_amount": oop_amount,
                        "decision": decision,
                        "model": selected_model,
                        "scenario": current_scenario,
                        "session_id": st.session_state.session_id
                    }
                    t_call_start = time.time()
                    response = requests.post(
                        f"{ORCHESTRATOR_URL}/submit",
                        json=payload,
                        timeout=REQUEST_TIMEOUT_SECONDS
                    )
                    call_elapsed_ms = int((time.time() - t_call_start) * 1000)

                    if response.status_code == 200:
                        resp_json = response.json()
                        if resp_json.get("success"):
                            result = resp_json.get("data", {})
                            telemetry = resp_json.get("telemetry", {})
                            if "round_trip_ms" not in telemetry:
                                telemetry["round_trip_ms"] = call_elapsed_ms
                            if "within_10s_limiter" not in telemetry:
                                telemetry["within_10s_limiter"] = call_elapsed_ms <= 10000
                            if "model_name" not in telemetry:
                                telemetry["model_name"] = selected_model

                            st.session_state.telemetry_logs.append({
                                "agent": "Judge Agent",
                                "action": "Assessment Evaluation",
                                "round_trip_ms": call_elapsed_ms,
                                "within_10s_limiter": call_elapsed_ms <= 10000,
                                "model_name": telemetry.get("model_name", selected_model),
                                "telemetry": telemetry,
                                "result": result,
                                "scenario_id": current_scenario.get("id"),
                                "plan_class": plan_class,
                                "claim_ref": current_scenario["provider"]["claim_ref"],
                                "trainee_input": {
                                    "eligible_amount": eligible_amount,
                                    "oop_amount": oop_amount,
                                    "decision": decision,
                                    "eob_code": eob_code
                                }
                            })

                            st.write("### Assessment Result")
                            if result.get("Status") == "Pass":
                                st.success(f"**Score:** {result.get('Score')}% | **Status:** {result.get('Status')}\n\n**Feedback:** {result.get('Feedback')}")
                            else:
                                st.error(f"**Score:** {result.get('Score')}% | **Status:** {result.get('Status')}\n\n**Feedback:** {result.get('Feedback')}")

                            st.info(
                                f"🔍 **AI Governance:** Latency: **{call_elapsed_ms/1000:.2f}s** "
                                f"(10s limiter: {'✅ PASS' if call_elapsed_ms <= 10000 else '⚠️ BREACH'}) | "
                                f"Tokens: **{telemetry.get('total_tokens', 0):,}**. Inspect in "
                                f"**🧠 AI Transparency & Token Telemetry Walkthrough** above."
                            )
                        else:
                            st.error(f"Evaluator error: {resp_json.get('error')}")
                    else:
                        st.error(f"Error from Orchestrator: {response.status_code} - {response.text}")
                except requests.exceptions.Timeout:
                    st.error("⏱️ **Request Timeout:** The evaluation took longer than 30s. The external Gemini API may be experiencing cold start or network latency. Please retry.")
                except Exception as e:
                    st.error(f"Error communicating with Orchestrator: {e}")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align: center; color: #475569; font-size: 0.8rem; margin-top: 2rem; margin-bottom: 3rem;'>"
        "--- End of Claim Adjudication Form ---</div>",
        unsafe_allow_html=True
    )
