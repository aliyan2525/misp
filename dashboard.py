import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

# Defaults to localhost for local dev; docker-compose overrides this to
# "http://api:8000" so the dashboard container can reach the api container
# by its service name.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Marketing Intelligence Platform", layout="wide")

# Track authentication tokens globally within user sessions
if "token" not in st.session_state:
    st.session_state.token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

def get_auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

def try_refresh_token():
    """Attempt to silently get a new access token using the stored refresh token.
    Returns True if successful, False if the refresh token is also expired/invalid."""
    if not st.session_state.refresh_token:
        return False
    try:
        resp = requests.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": st.session_state.refresh_token}
        )
        if resp.status_code == 200:
            st.session_state.token = resp.json()["access_token"]
            return True
    except Exception:
        pass
    return False

# ==========================================
# GATEKEEPER VIEW (Logged Out)
# ==========================================
if st.session_state.token is None:
    st.title("🔐 Marketing Intelligence Gateway")
    st.subheader("Please access your designated workspace profile or create an instance below.")
    
    tab_login, tab_signup = st.tabs(["Existing User Login", "New Organization Sign Up"])
    
    with tab_login:
        login_email = st.text_input("Corporate Email Address", key="login_email_input")
        login_password = st.text_input("Password Verification", type="password", key="login_pwd_input")
        
        if st.button("Sign In to Workspace", use_container_width=True):
            payload = {"email": login_email, "password": login_password}
            try:
                response = requests.post(f"{API_URL}/auth/login", json=payload)
                if response.status_code == 200:
                    login_data = response.json()
                    st.session_state.token = login_data["access_token"]
                    st.session_state.refresh_token = login_data["refresh_token"]
                    st.success("Session Verified! Fetching telemetry streams...")
                    st.rerun()
                else:
                    st.error(f"Authentication Rejected: {response.json().get('detail', 'Invalid Username/Password')}")
            except Exception as e:
                st.error(f"Unable to connect to Core Backend API Service: {str(e)}")
                
    with tab_signup:
        reg_full_name = st.text_input("Account Owner Full Name", key="reg_name")
        reg_org_name = st.text_input("Corporate Organization / Company Context", key="reg_org")
        reg_email = st.text_input("Primary Contact Email", key="reg_email")
        reg_password = st.text_input("Secure Account Password", type="password", key="reg_pwd")
        
        if st.button("Provision Multi-Tenant Workspace", use_container_width=True):
            payload = {
                "email": reg_email,
                "password": reg_password,
                "full_name": reg_full_name,
                "org_name": reg_org_name
            }
            try:
                response = requests.post(f"{API_URL}/auth/signup", json=payload)
                if response.status_code == 200:
                    st.success("Tenant Workspace Provisioned! Switch to the Login tab to continue.")
                else:
                    st.error(f"Provisioning Failed: {response.json().get('detail', 'Malformed input metrics')}")
            except Exception as e:
                st.error(f"Core Engine API currently offline: {str(e)}")

# ==========================================
# ENTERPRISE WORKSPACE GRAPH GRID (Logged In)
# ==========================================
else:
    headers = get_auth_headers()
    
    with st.sidebar:
        st.write("🟢 Workspace Protection Active")
        st.markdown("---")
        
        st.subheader("📥 Data Feed Sync Engine")
        uploaded_file = st.file_uploader("Drop Performance Tracking CSV", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("Parse & Commit Records", use_container_width=True):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                try:
                    upload_res = requests.post(
                        f"{API_URL}/api/data/upload", 
                        headers=headers, 
                        files=files
                    )
                    if upload_res.status_code == 200:
                        st.sidebar.success("Database records synchronized cleanly!")
                        st.rerun()
                    else:
                        st.sidebar.error(f"Sync Interrupted: {upload_res.json().get('detail')}")
                except Exception as e:
                    st.sidebar.error(f"Gateway execution error: {str(e)}")
                    
        st.markdown("---")
        st.subheader("📄 Reporting")
        if st.button("Generate PDF Report", use_container_width=True):
            try:
                pdf_response = requests.get(f"{API_URL}/api/reports/pdf", headers=headers)
                if pdf_response.status_code == 200:
                    st.download_button(
                        "⬇️ Click to save your report",
                        data=pdf_response.content,
                        file_name="marketing_report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error(f"Report generation failed: {pdf_response.status_code}")
            except Exception as e:
                st.error(f"Reporting service error: {str(e)}")

        st.markdown("---")
        if st.button("Terminate Session Profile", use_container_width=True):
            st.session_state.token = None
            st.session_state.refresh_token = None
            st.rerun()
            
    st.title("📊 Enterprise Performance Workspace")
    st.markdown("---")
    
    try:
        summary_res = requests.get(f"{API_URL}/api/metrics/summary", headers=headers)
        channels_res = requests.get(f"{API_URL}/api/metrics/channels", headers=headers)
        performance_res = requests.get(f"{API_URL}/api/metrics/performance", headers=headers)
        
        if summary_res.status_code == 401:
            if try_refresh_token():
                st.rerun()  # retry the whole page load with the new access token
            else:
                st.error("Your session has fully expired. Please log in again.")
                st.session_state.token = None
                st.session_state.refresh_token = None
                st.rerun()
            
        if summary_res.status_code == 200 and channels_res.status_code == 200 and performance_res.status_code == 200:
            summary_data = summary_res.json()
            channels_data = channels_res.json()
            performance_data = performance_res.json()
            
            # Key Index Performance Grid Matrix
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Total Ad-Spend Assets Allocated", value=f"${summary_data.get('total_spend', 0.0):,.2f}")
            with col2:
                st.metric(label="Aggregated Conversion Events", value=f"{summary_data.get('total_conversions', 0):,}")
            with col3:
                st.metric(label="Valid Funnel Interaction Clicks", value=f"{summary_data.get('total_clicks', 0):,}")
                
            st.markdown("---")
            
            # Interactive Graph Visualization Layouts
            left_chart_frame, right_chart_frame = st.columns(2)
            
            with left_chart_frame:
                st.subheader("📈 Core Attribution Trends Over Time")
                if isinstance(channels_data, list) and len(channels_data) > 0:
                    df_channels = pd.DataFrame(channels_data)
                    fig_line = px.line(
                        df_channels, 
                        x="metric_date", 
                        y="total_conversions", 
                        color="channel", 
                        title="Incremental Daily Funnel Returns"
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("No timeline performance tracking logs found for this tenant workspace framework.")
                    
            with right_chart_frame:
                st.subheader("🎯 Acquisition & ROI Efficiencies")
                if isinstance(performance_data, list) and len(performance_data) > 0:
                    df_perf = pd.DataFrame(performance_data)
                    fig_bar = px.bar(
                        df_perf, 
                        x="channel", 
                        y="conversions_per_hundred_dollars", 
                        color="channel", 
                        title="Acquisitions Generated Per $100 Ad-Spend Allocation"
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("No active performance calculations compiled for this configuration profile.")

            # ==========================================
            # Phase 6 — Recommendation Engine Section
            # ==========================================
            st.markdown("---")
            st.subheader("💡 Recommendations")
            try:
                rec_res = requests.get(f"{API_URL}/api/recommendations", headers=headers)
                if rec_res.status_code == 200:
                    recs = rec_res.json().get("recommendations", [])
                    if recs:
                        for rec in recs:
                            if rec["priority"] == "high":
                                st.error(f"**{rec['campaign']}**: {rec['recommendation']}")
                            else:
                                st.warning(f"**{rec['campaign']}**: {rec['recommendation']}")
                    else:
                        st.info("No recommendations yet — upload more campaign data to generate insights.")
                else:
                    st.error(f"Could not load recommendations: {rec_res.status_code}")
            except Exception as e:
                st.error(f"Recommendation engine connection error: {str(e)}")

        else:
            st.error("⚠️ Data Aggregation Framework Error Encountered")
            st.warning(f"Summary Response Status: {summary_res.status_code} | Reason: {summary_res.text}")
            
    except Exception as e:
        st.error(f"Visual dashboard layer encountered processing exception: {str(e)}")
