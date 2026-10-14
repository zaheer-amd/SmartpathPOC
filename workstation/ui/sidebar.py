"""
SmartPath Workstation Sidebar Component

Renders session configuration, API key input, model selection, queue management,
and active terminal metadata.
"""

from typing import Any
import streamlit as st
import google.generativeai as genai
import requests
from config import ORCHESTRATOR_URL, DEFAULT_MODEL, FALLBACK_MODEL


def render_sidebar(scenarios: list[dict[str, Any]]) -> tuple[str, str, dict[str, Any], str]:
    """
    Renders sidebar configuration and queue management.

    Returns:
        (api_key, selected_model, current_scenario, plan_class)
    """
    st.sidebar.header("⚙️ System & Session Config")
    api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password")

    if not api_key:
        st.warning("👈 Please enter your free Gemini API key in the sidebar to start the simulation.")
        st.stop()

    # Configure Gemini and fetch available models
    genai.configure(api_key=api_key)
    try:
        available_models = [
            m.name.replace("models/", "")
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        ]
        st.sidebar.success("API Key accepted!")
        default_idx = (
            available_models.index(DEFAULT_MODEL)
            if DEFAULT_MODEL in available_models else 0
        )
        selected_model = st.sidebar.selectbox("Select Model:", available_models, index=default_idx)
    except Exception as e:
        st.sidebar.error(f"Error checking API key: {e}")
        selected_model = FALLBACK_MODEL

    # Initialize session states
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "telemetry_logs" not in st.session_state:
        st.session_state.telemetry_logs = []
    if "current_scenario_index" not in st.session_state:
        st.session_state.current_scenario_index = 0
    if "session_id" not in st.session_state:
        st.session_state.session_id = None

    current_scenario = scenarios[st.session_state.current_scenario_index]
    plan_class = current_scenario["plan_class"]

    # Start a new session with the Akka orchestrator on first load
    if st.session_state.session_id is None:
        try:
            resp = requests.post(
                f"{ORCHESTRATOR_URL}/session/start",
                json={
                    "trainee_id": "OPR-5524",
                    "plan_class": plan_class
                },
                timeout=5
            )
            if resp.status_code == 200:
                st.session_state.session_id = resp.json().get("session_id")
        except requests.exceptions.RequestException:
            st.session_state.session_id = "local-fallback"

    # Sidebar Queue Controls
    st.sidebar.markdown("---")
    st.sidebar.header("🔄 Queue Management")
    if st.sidebar.button("⏭️ Next Claim in Queue", use_container_width=True, type="primary"):
        st.session_state.current_scenario_index = (st.session_state.current_scenario_index + 1) % len(scenarios)
        st.session_state.chat_history = []
        st.session_state.session_id = None
        st.rerun()

    # Sidebar Terminal Session Details
    with st.sidebar.expander("🖥️ Active Terminal Session", expanded=False):
        st.text(
            f"Station ID: TERM-WS09-AUSTIN\n"
            f"Operator: OPR-5524 (Trainee - Level 1)\n"
            f"Environment: PROD-US-CENTRAL (Austin DC)\n"
            f"Workpool: US-COMM-CSD-MANUAL-02\n"
            f"Active Plan Class: {plan_class}"
        )

    # Active session badge
    if st.session_state.session_id and st.session_state.session_id != "local-fallback":
        st.sidebar.info(f"📋 Session: `{st.session_state.session_id[:8]}...`")

    # AI Governance Callout
    st.sidebar.markdown("---")
    st.sidebar.header("🧠 AI Governance & Audit")
    st.sidebar.markdown("""
    <div style="background: rgba(14, 165, 233, 0.08); border: 1px solid #0284c7; border-radius: 6px; padding: 10px; font-size: 0.8rem; color: #bae6fd; line-height: 1.4;">
        <strong>🔎 Transparency & Token Walkthrough:</strong><br>
        Click the tab <strong>'🧠 AI Transparency & Token Telemetry Walkthrough'</strong> above to inspect the 5-layer prompt breakdown, step-level tokens, and JSON efficiency savings.
    </div>
    """, unsafe_allow_html=True)

    return api_key, selected_model, current_scenario, plan_class
