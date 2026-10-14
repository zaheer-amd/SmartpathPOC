"""
SmartPath Workstation Claim Form Component

Renders the claims adjudication form panels:
1. Group & Subscriber Information (Eligibility Ledger)
2. Claim Line & Provider Details (Scanned Invoice Data)
3. System Rule Checks & Member Claim History
4. Scanned Document Invoice Image Viewer
"""

import os
from typing import Any
import streamlit as st
from config import WORKSTATION_ROOT


def render_claim_form(current_scenario: dict[str, Any]) -> None:
    """Renders the four main claim verification and context expanders."""
    st.subheader("📋 Claim Adjudication Form (GLH Workstation - US Edition)")

    # 1. Member & Group Information
    with st.expander("👤 Group & Subscriber Information (Eligibility Ledger)", expanded=True):
        m = current_scenario["member"]
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.text_input("Employer / Group Sponsor", value=m["employer"], disabled=True)
            st.text_input("Subscriber ID / SSN Hash", value=m["subscriber_id"], disabled=True)
            st.text_input("Subscriber / Patient Name", value=m["name"], disabled=True)
            st.text_input("Dep Sequence & Relation", value=m["relation"], disabled=True)
            st.text_input("State / Tax Jurisdiction", value=m["state_tax"], disabled=True)
            st.text_input("Division & Cost Center", value=m["division"], disabled=True)
        with m_col2:
            st.text_input("Coverage Status", value=m["status"], disabled=True)
            st.text_input("Effective / Expiration Date", value=m["effective_dates"], disabled=True)
            st.text_input("Plan Class & Network", value=m["plan_network"], disabled=True)
            st.text_input("Date of Birth & Gender", value=m["dob_gender"], disabled=True)
            st.text_input("Coordination of Benefits (COB)", value=m["cob"], disabled=True)
            st.text_input("Annual Deductible Accumulator", value=m["deductible"], disabled=True)

    # 2. Claim Line & Provider Details
    with st.expander("📄 Claim Line & Provider Details (Scanned Invoice Data)", expanded=False):
        p = current_scenario["provider"]
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.text_input("Claim Reference ID", value=p["claim_ref"], disabled=True)
            st.text_input("Provider Facility & Name", value=p["facility"], disabled=True)
            st.text_input("Provider NPI & State License", value=p["license"], disabled=True)
            st.text_input("Provider Taxonomy Code", value=p["taxonomy"], disabled=True)
            st.text_input("Total Receipt / Billed ($)", value=f"${p['billed']:.2f} USD", disabled=True)
            st.text_input("Facility Address", value=p["address"], disabled=True)
        with c_col2:
            st.text_input("Date of Service (DOS)", value=p["dos"], disabled=True)
            st.text_input("Receipt / Invoice No", value=p["invoice_no"], disabled=True)
            st.text_input("Billing Code (CPT / HCPCS)", value=p["cpt"], disabled=True)
            st.text_input("Diagnosis Code (ICD-10-CM)", value=p["icd"], disabled=True)
            st.text_input("Benefit Grid Rule", value=p["rule"], disabled=True)
            st.text_input("Payee / Assignment Code", value=p["payee"], disabled=True)

    # 3. System Rule Verifications & Claim History Ledger
    with st.expander("📜 System Rule Checks & Member Claim History", expanded=False):
        if current_scenario.get("history"):
            st.dataframe(current_scenario["history"], use_container_width=True, hide_index=True)
        else:
            st.info("No prior claims on file for this subscriber.")

    # 4. Invoice Image Viewer
    with st.expander("📸 View Scanned Document (Invoice/Receipt)", expanded=False):
        raw_img_path = current_scenario.get("invoice_image", "")
        # Resolve path whether running from root or workstation/
        resolved_img_path = raw_img_path
        if not os.path.exists(resolved_img_path):
            resolved_img_path = str(WORKSTATION_ROOT / raw_img_path)
        if not os.path.exists(resolved_img_path):
            resolved_img_path = str(WORKSTATION_ROOT / "data" / os.path.basename(raw_img_path))

        if os.path.exists(resolved_img_path):
            st.image(resolved_img_path, caption="Original Scanned Submission", width=580)
        else:
            st.error(f"Document image missing or not found at: {raw_img_path}")
