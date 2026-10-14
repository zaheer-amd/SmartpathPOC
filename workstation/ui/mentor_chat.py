"""
SmartPath Workstation Mentor Chat Component

Renders the live assistant interface:
1. Active policy rules expander (retrieved via Gateway RAG endpoint over HTTP)
2. Interactive chat history container
3. Chat input sending questions to Akka Orchestrator over HTTP
4. Real-time pedagogical response and token telemetry recording
"""

import time
from typing import Any
import streamlit as st
import requests
from config import ORCHESTRATOR_URL, get_policy_url, REQUEST_TIMEOUT_SECONDS, POLICY_TIMEOUT_SECONDS


def render_mentor_chat(
    current_scenario: dict[str, Any],
    plan_class: str,
    api_key: str,
    selected_model: str
) -> None:
    """Renders the AI mentor chat panel and policy documentation expander."""
    st.subheader("💬 Live Assistant (Mentor Agent)")
    st.caption(f"Ask questions about the current **{plan_class}** policy rules or limit calculations.")

    # 1. Active policy viewer (HTTP call to Gateway)
    with st.expander(f"📘 View Active Policy Rules ({plan_class})", expanded=False):
        policy_container = st.container(height=400)
        with policy_container:
            try:
                resp = requests.get(get_policy_url(plan_class), timeout=POLICY_TIMEOUT_SECONDS)
                if resp.status_code == 200 and resp.json().get("success"):
                    st.markdown(resp.json().get("content"))
                else:
                    st.error("Could not load policy rules.")
            except Exception:
                st.warning("RAG Service is not running. Could not load policy rules.")

    # 2. Existing chat history
    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(message)

    # 3. Chat input
    user_question = st.chat_input("Ask for help with the claim policy or calculation...")

    if user_question:
        st.session_state.chat_history.append(("user", user_question))
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "api_key": api_key,
                        "plan_class": plan_class,
                        "message": user_question,
                        "model": selected_model,
                        "scenario": current_scenario,
                        "session_id": st.session_state.session_id
                    }
                    t_chat_start = time.time()
                    response = requests.post(
                        f"{ORCHESTRATOR_URL}/chat",
                        json=payload,
                        timeout=REQUEST_TIMEOUT_SECONDS
                    )
                    chat_elapsed_ms = int((time.time() - t_chat_start) * 1000)

                    if response.status_code == 200:
                        resp_json = response.json()
                        if resp_json.get("success"):
                            mentor_response = resp_json.get("data")
                            telemetry = resp_json.get("telemetry", {})
                            if "round_trip_ms" not in telemetry:
                                telemetry["round_trip_ms"] = chat_elapsed_ms
                            if "within_10s_limiter" not in telemetry:
                                telemetry["within_10s_limiter"] = chat_elapsed_ms <= 10000
                            if "model_name" not in telemetry:
                                telemetry["model_name"] = selected_model

                            st.session_state.telemetry_logs.append({
                                "agent": "Mentor Agent",
                                "action": "Chat Assistance",
                                "round_trip_ms": chat_elapsed_ms,
                                "within_10s_limiter": chat_elapsed_ms <= 10000,
                                "model_name": telemetry.get("model_name", selected_model),
                                "telemetry": telemetry,
                                "user_question": user_question,
                                "mentor_response": mentor_response,
                                "scenario_id": current_scenario.get("id"),
                                "plan_class": plan_class,
                                "claim_ref": current_scenario["provider"]["claim_ref"]
                            })

                            st.markdown(mentor_response)
                            st.session_state.chat_history.append(("assistant", mentor_response))
                            st.caption(
                                f"🔍 Latency: **{chat_elapsed_ms/1000:.2f}s** | "
                                f"Tokens: **{telemetry.get('total_tokens', 0):,}** | "
                                f"Socratic hint captured in **🧠 AI Transparency & Token Telemetry Walkthrough** tab above."
                            )
                        else:
                            st.error(f"Mentor error: {resp_json.get('error')}")
                    else:
                        st.error(f"Error from Orchestrator: {response.status_code} - {response.text}")
                except requests.exceptions.Timeout:
                    st.error("⏱️ **Request Timeout:** The assistant took longer than 30s to respond. Please retry.")
                except Exception as e:
                    st.error(f"Error communicating with Orchestrator: {e}")
