"""
HemoStat Dashboard Main Application

Real-time Streamlit dashboard for monitoring HemoStat container health system.
Displays live container metrics, active issues, remediation history, and event timeline
with auto-refresh every 5 seconds.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from dotenv import load_dotenv

from agents.logger import HemoStatLogger
from dashboard.components import (
    render_active_issues,
    render_health_grid,
    render_metrics_cards,
    render_remediation_history,
    render_timeline,
)
from dashboard.data_fetcher import (
    get_active_containers,
    get_all_events,
    get_events_by_type,
    get_false_alarm_count,
    get_redis_client,
    get_remediation_stats,
)

# Load environment variables
load_dotenv()

# Initialize logger
logger = HemoStatLogger.get_logger("dashboard")

# Page configuration
st.set_page_config(
    page_title="HemoStat Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling - Modern blue and teal theme with consistent color palette
st.markdown("""
<style>
    /* Color palette */
    :root {
        --primary-blue: #0066cc;
        --secondary-blue: #003d99;
        --accent-teal: #00b4d8;
        --accent-green: #06d6a0;
        --accent-red: #ef476f;
        --accent-yellow: #ffd166;
        --neutral-light: #f0f4f8;
        --neutral-lighter: #f8fafc;
        --neutral-dark: #1a202c;
        --text-primary: #2d3748;
        --text-secondary: #718096;
    }
    
    /* Overall page background - ensure white */
    body {
        background-color: #ffffff !important;
    }
    
    /* Page background - white */
    .stApp {
        background: #ffffff !important;
    }
    
    /* Main container - clean light background */
    .main {
        background: linear-gradient(135deg, #f8fafc 0%, #f0f4f8 100%) !important;
    }
    
    /* Block container background */
    .block-container {
        background: transparent !important;
    }
    
    /* Sidebar - modern blue gradient */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #003d99 0%, #0066cc 50%, #00b4d8 100%);
        color: white;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
        border: none !important;
    }
    
    /* Headers - professional blue with teal accent */
    h1, h2, h3 {
        color: #003d99;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    h1 {
        margin-bottom: 24px;
        line-height: 1.3;
    }
    
    h2 {
        border-left: 4px solid #0066cc;
        padding-left: 20px;
        margin-top: 20px;
        margin-bottom: 16px;
    }
    
    h3 {
        color: #0066cc;
        margin-top: 16px;
    }
    
    /* Metric cards - blue gradient with teal accents */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #f0f4f8 0%, #e8f0ff 100%) !important;
        border-radius: 12px !important;
        border-left: 4px solid #0066cc !important;
        border-top: 1px solid rgba(0, 180, 216, 0.2) !important;
        box-shadow: 0 2px 12px rgba(0, 102, 204, 0.08) !important;
        padding: 20px !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="metric-container"] label {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #003d99 !important;
        letter-spacing: 0.5px !important;
        text-transform: uppercase !important;
    }
    
    [data-testid="metric-container"] [data-testid="metric-value"] {
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #0066cc !important;
        font-family: 'Segoe UI', 'Helvetica Neue', sans-serif !important;
    }
    
    [data-testid="metric-container"]:hover {
        box-shadow: 0 4px 20px rgba(0, 102, 204, 0.15) !important;
        transform: translateY(-2px) !important;
        border-left-color: #00b4d8 !important;
        background: linear-gradient(135deg, #e8f0ff 0%, #dce8ff 100%) !important;
    }
    
    /* Data frames - clean with blue borders */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 6px rgba(0, 102, 204, 0.08);
        border: 1px solid rgba(0, 102, 204, 0.12);
        background: white;
    }
    
    /* Buttons - blue with teal hover */
    button {
        background: linear-gradient(135deg, #0066cc 0%, #003d99 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        padding: 12px 24px !important;
        transition: all 0.2s ease !important;
    }
    
    /* Hide icon text in expanders and buttons */
    button svg,
    button img,
    [class*="stIconMaterial"],
    .material-icons,
    [data-testid="StyledLinkIconContainer"],
    span[data-testid] > span:only-child:not([class]) {
        display: none !important;
    }
    
    /* Hide Material Icons text specifically */
    span:has(.material-icons),
    div:has(.material-icons) {
        font-size: 0 !important;
    }
    
    /* Force hide any element containing icon text keywords */
    *:contains("keyboard"),
    *:contains("arrow") {
        font-size: 0px !important;
    }
    
    button:hover {
        background: linear-gradient(135deg, #00b4d8 0%, #0066cc 100%) !important;
        box-shadow: 0 4px 12px rgba(0, 180, 216, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Containers and cards */
    [data-testid="stContainer"] {
        border-radius: 8px;
    }
    
    /* Expanders - blue themed */
    [data-testid="stExpander"] {
        border: 1px solid rgba(0, 102, 204, 0.15);
        border-radius: 8px;
        background: linear-gradient(135deg, #f8fafc 0%, #f0f4f8 100%);
    }
    
    /* Hide the jumbled icon text completely */
    [data-testid="stExpander"] summary > span {
        position: relative;
        padding-left: 24px;
    }
    
    [data-testid="stExpander"] summary > span > span {
        font-size: 0 !important;
        display: none !important;
    }
    
    /* Create custom arrow using CSS */
    [data-testid="stExpander"] summary > span::before {
        content: "" !important;
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%) rotate(90deg);
        width: 0;
        height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-top: 8px solid #0066cc;
        transition: transform 0.2s ease;
    }
    
    /* Rotate arrow when collapsed */
    [data-testid="stExpander"]:not([open]) summary > span::before {
        transform: translateY(-50%) rotate(0deg) !important;
    }
    
    [data-testid="stExpander"] summary {
        color: #003d99;
        font-weight: 600;
    }
    
    [data-testid="stExpander"] summary:hover {
        color: #0066cc;
    }
    
    /* Tabs - modern with blue accent */
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 2px solid rgba(0, 102, 204, 0.1);
        display: flex;
        gap: 0;
    }
    
    [data-testid="stTabs"] [role="tab"] {
        color: white !important;
        font-weight: 600;
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
        flex: 1;
        text-align: center;
        padding: 12px 20px;
        background: #0066cc;
        border-radius: 8px 8px 0 0;
        margin-right: 4px;
    }
    
    [data-testid="stTabs"] [role="tab"] * {
        color: white !important;
    }
    
    [data-testid="stTabs"] [role="tab"] p,
    [data-testid="stTabs"] [role="tab"] span,
    [data-testid="stTabs"] [role="tab"] div {
        color: white !important;
    }
    
    [data-testid="stTabs"] [role="tab"]:hover {
        background: #003d99;
    }
    
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: #00b4d8;
        border-bottom-color: #00b4d8;
    }
    
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] * {
        color: white !important;
    }
    
    /* Status indicators - semantic colors */
    .status-healthy {
        color: #06d6a0;
        font-weight: 700;
    }
    
    .status-unhealthy {
        color: #ef476f;
        font-weight: 700;
    }
    
    .status-warning {
        color: #ffd166;
        font-weight: 700;
    }
    
    .status-deploying {
        color: #00b4d8;
        font-weight: 700;
    }
    
    /* Chart containers - clean blue style */
    [data-testid="stPlotlyContainer"] {
        border-radius: 8px;
        background: white;
        padding: 16px;
        box-shadow: 0 1px 6px rgba(0, 102, 204, 0.08);
        border: 1px solid rgba(0, 102, 204, 0.12);
    }
    
    
    /* Hide Vega-Lite and Altair action buttons */
    .vega-embed summary,
    .vega-embed details,
    .vega-actions,
    .vega-bindings,
    [data-testid="stVegaLiteChart"] details,
    [data-testid="stVegaLiteChart"] summary {
        display: none !important;
    }
    
    # /* Hide Streamlit element toolbar buttons (fullscreen, etc.) */
    # [data-testid="stBaseButton-elementToolbar"],
    # [data-testid="stElementToolbar"],
    # button[kind="elementToolbar"] {
    #     display: none !important;
    # }
    
    /* Dividers - subtle blue gradient */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 102, 204, 0.2), transparent);
        margin: 24px 0;
    }
    
    /* Text styling - improved readability */
    p, span, label {
        color: #2d3748;
        line-height: 1.6;
        font-size: 14px;
    }
    
    /* Captions - secondary text */
    .stCaption {
        color: #718096 !important;
    }
    
    /* Info boxes - blue themed alerts */
    [data-testid="stAlert"] {
        border-radius: 8px;
        border-left: 4px solid #0066cc;
        background: linear-gradient(135deg, rgba(0, 102, 204, 0.05) 0%, rgba(0, 180, 216, 0.05) 100%);
    }
    
    /* Code blocks - terminal style with blue accent */
    code {
        background: #1a202c;
        color: #06d6a0;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
    }
    
    /* Links - blue themed */
    a {
        color: #0066cc !important;
        text-decoration: none;
    }
    
    a:hover {
        color: #00b4d8 !important;
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if "auto_refresh_enabled" not in st.session_state:
    auto_refresh_env = os.getenv("DASHBOARD_AUTO_REFRESH", "true").lower() == "true"
    st.session_state.auto_refresh_enabled = auto_refresh_env
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", 5))
if "max_events" not in st.session_state:
    st.session_state.max_events = int(os.getenv("DASHBOARD_MAX_EVENTS", 1000))
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None
if "manual_refresh_trigger" not in st.session_state:
    st.session_state.manual_refresh_trigger = 0


def check_redis_connection() -> bool:
    """
    Test Redis connection and return status.

    Returns:
        bool: True if Redis is connected, False otherwise
    """
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def render_sidebar() -> None:
    """
    Render sidebar with system status, controls, and links.

    Displays Redis connection status, refresh controls, settings, and
    helpful links to documentation and repositories.
    """
    st.sidebar.title("HemoStat")

    # System status
    redis_connected = check_redis_connection()
    status_text = "Connected" if redis_connected else "Disconnected"
    st.sidebar.markdown(f"**Status**: {status_text}")

    if st.session_state.last_refresh:
        tz_abbr = st.session_state.last_refresh.strftime("%Z")  # EST or EDT
        st.sidebar.write(f"**Last Refresh**: {st.session_state.last_refresh.strftime(f'%I:%M:%S %p {tz_abbr}')}")

    st.sidebar.markdown("---")

    # Manual refresh button
    if st.sidebar.button("Refresh Now", use_container_width=True):
        st.session_state.manual_refresh_trigger += 1
        st.cache_data.clear()

    st.sidebar.markdown("---")

    # Settings
    st.sidebar.markdown("**Settings**")
    st.session_state.auto_refresh_enabled = st.sidebar.checkbox(
        "Auto-refresh",
        value=st.session_state.auto_refresh_enabled,
    )

    st.session_state.refresh_interval = st.sidebar.slider(
        "Interval (seconds)",
        min_value=1,
        max_value=60,
        value=st.session_state.refresh_interval,
        step=1,
    )

    st.sidebar.markdown("---")

    # Links
    st.sidebar.markdown("**Resources**")
    st.sidebar.markdown(
        """
        - [Documentation](https://github.com/jondmarien/HemoStat)
        - [GitHub](https://github.com/jondmarien/HemoStat)
        - [API Docs](./docs/API_PROTOCOL.md)
        """
    )


def render_header() -> None:
    """
    Render dashboard header with title and connection status.

    Displays main title, subtitle with current timestamp, and
    connection status indicator.
    """
    eastern = ZoneInfo("America/New_York")
    now_et = datetime.now(eastern)
    tz_abbr = now_et.strftime("%Z")  # EST or EDT
    
    col1, col2 = st.columns([3, 1], gap="large")
    
    with col1:
        st.markdown("<h2 style='border-left: 4px solid #0066cc; padding-left: 18px; margin-bottom: 0;'>HemoStat Container Health Monitoring</h2>", unsafe_allow_html=True)
        st.caption(f"Real-time autonomous monitoring • {now_et.strftime(f'%Y-%m-%d %I:%M:%S %p {tz_abbr}')}")

    with col2:
        redis_connected = check_redis_connection()
        status_indicator = "Connected" if redis_connected else "Disconnected"
        status_color = "#00aa44" if redis_connected else "#cc0000"
        st.markdown(
            f"<div style='text-align: right; padding: 12px; border-radius: 8px; "
            f"background: rgba(0, 102, 204, 0.05); border-left: 3px solid {status_color};'>"
            f"<div style='font-size: 12px; color: #666; margin-bottom: 4px;'>System Status</div>"
            f"<div style='font-size: 14px; font-weight: 600; color: {status_color};'>"
            f"Redis {status_indicator}</div></div>",
            unsafe_allow_html=True
        )


def render_live_content() -> None:
    """
    Render auto-refreshing dashboard content.

    Uses st.fragment with dynamic run_every interval tied to session state.
    Fetches data from Redis and renders all dashboard tabs.
    Tabs are outside fragment to preserve selection across refreshes.
    """
    
    if not st.session_state.auto_refresh_enabled:
        st.info("Auto-refresh is disabled. Click 'Refresh Now' to update.")
        return

    # Fetch data with fragment for auto-refresh
    @st.fragment(run_every=st.session_state.refresh_interval)  # type: ignore[attr-defined]
    def fetch_data() -> tuple:
        eastern = ZoneInfo("America/New_York")
        st.session_state.last_refresh = datetime.now(eastern)
        
        try:
            with st.spinner("Loading data from Redis..."):
                all_events = get_all_events(limit=st.session_state.max_events)
                remediation_events = get_events_by_type(
                    "remediation_complete", limit=st.session_state.max_events
                )
                false_alarm_count = get_false_alarm_count()
                active_containers = len(get_active_containers())
                remediation_stats = get_remediation_stats()
            
            return all_events, remediation_events, false_alarm_count, active_containers, remediation_stats
        except Exception as e:
            logger.error(f"Error fetching dashboard data: {e}")
            st.error(f"Error loading dashboard data: {e}")
            return [], [], 0, 0, {"success_rate": 0.0, "total_remediations": 0, "false_alarms": 0}

    # Fetch data (will auto-refresh)
    all_events, remediation_events, false_alarm_count, active_containers, remediation_stats = fetch_data()

    # Metrics section (outside fragment)
    st.subheader("Key Metrics")
    render_metrics_cards(remediation_stats, false_alarm_count, active_containers)

    # Tabs for different views (outside fragment to preserve tab state)
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Health Grid", "Active Issues", "History", "Timeline"]
    )

    with tab1:
        st.subheader("Container Health Grid")
        render_health_grid(all_events)

    with tab2:
        st.subheader("Active Issues")
        render_active_issues(all_events)

    with tab3:
        st.subheader("Remediation History")
        render_remediation_history(remediation_events)

    with tab4:
        st.subheader("Event Timeline")
        render_timeline(all_events, max_events=st.session_state.max_events)


def render_footer() -> None:
    """
    Render dashboard footer with version and status information.

    Displays HemoStat version and last update timestamp.
    """
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.caption("HemoStat v0.1.0 • Phase 4: Testing & Integration")

    with col2:
        if st.session_state.last_refresh:
            tz_abbr = st.session_state.last_refresh.strftime("%Z")
            st.caption(f"Last updated: {st.session_state.last_refresh.strftime(f'%I:%M:%S %p {tz_abbr}')}")


def main() -> None:
    """
    Main dashboard application entry point.

    Initializes the dashboard, renders sidebar, header, content, and footer.
    """
    logger.info("Dashboard started")

    # Render sidebar
    render_sidebar()

    # Render header
    render_header()

    # Render main content
    render_live_content()

    # Render footer
    render_footer()


if __name__ == "__main__":
    main()
