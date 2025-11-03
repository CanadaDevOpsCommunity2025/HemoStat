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

# Custom CSS styling - clinical/medical + DevOps infrastructure theme
st.markdown("""
<style>
    /* Primary colors: Medical blue + DevOps infrastructure orange */
    :root {
        --primary-blue: #0066cc;
        --secondary-blue: #003d99;
        --devops-orange: #ff6b35;
        --accent-green: #00aa44;
        --accent-red: #cc0000;
        --accent-yellow: #ffaa00;
        --neutral-light: #f5f7fa;
        --neutral-dark: #1a1a1a;
    }
    
    /* Main container styling - subtle infrastructure grid pattern */
    .main {
        background: linear-gradient(135deg, #ffffff 0%, #f5f7fa 100%);
        background-image: 
            linear-gradient(0deg, transparent 24%, rgba(0, 102, 204, 0.02) 25%, rgba(0, 102, 204, 0.02) 26%, transparent 27%, transparent 74%, rgba(0, 102, 204, 0.02) 75%, rgba(0, 102, 204, 0.02) 76%, transparent 77%, transparent),
            linear-gradient(90deg, transparent 24%, rgba(0, 102, 204, 0.02) 25%, rgba(0, 102, 204, 0.02) 26%, transparent 27%, transparent 74%, rgba(0, 102, 204, 0.02) 75%, rgba(0, 102, 204, 0.02) 76%, transparent 77%, transparent);
        background-size: 50px 50px;
    }
    
    /* Sidebar styling - DevOps infrastructure gradient */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #003d99 0%, #0066cc 50%, #ff6b35 100%);
        color: white;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Headers - clean and professional with DevOps accent */
    h1, h2, h3 {
        color: #003d99;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    h1 {
        border-bottom: 3px solid #ff6b35;
        padding-bottom: 12px;
        margin-bottom: 24px;
    }
    
    h2 {
        border-left: 4px solid #ff6b35;
        padding-left: 12px;
    }
    
    /* Metric cards - elevated with DevOps accent */
    [data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        border-left: 4px solid #ff6b35;
        box-shadow: 0 2px 8px rgba(255, 107, 53, 0.1);
        padding: 20px;
        transition: all 0.3s ease;
    }
    
    [data-testid="metric-container"]:hover {
        box-shadow: 0 4px 16px rgba(255, 107, 53, 0.15);
        transform: translateY(-2px);
        border-left-color: #0066cc;
    }
    
    /* Data frames - infrastructure style */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(255, 107, 53, 0.1);
    }
    
    /* Buttons - DevOps orange with blue accent */
    button {
        background: linear-gradient(135deg, #ff6b35 0%, #ff5722 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    button:hover {
        background: linear-gradient(135deg, #ff5722 0%, #ff6b35 100%) !important;
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4) !important;
    }
    
    /* Containers and cards */
    [data-testid="stContainer"] {
        border-radius: 8px;
    }
    
    /* Expanders - DevOps infrastructure style */
    [data-testid="stExpander"] {
        border: 1px solid rgba(255, 107, 53, 0.2);
        border-radius: 8px;
        background: white;
    }
    
    [data-testid="stExpander"] summary {
        color: #003d99;
        font-weight: 500;
    }
    
    /* Tabs - modern with DevOps accent */
    [data-testid="stTabs"] [role="tablist"] {
        border-bottom: 2px solid rgba(255, 107, 53, 0.2);
    }
    
    [data-testid="stTabs"] [role="tab"] {
        color: #666;
        font-weight: 500;
        border-bottom: 3px solid transparent;
        transition: all 0.2s ease;
    }
    
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: #ff6b35;
        border-bottom-color: #ff6b35;
    }
    
    /* Status indicators - operational colors */
    .status-healthy {
        color: #00aa44;
        font-weight: 600;
    }
    
    .status-unhealthy {
        color: #cc0000;
        font-weight: 600;
    }
    
    .status-warning {
        color: #ffaa00;
        font-weight: 600;
    }
    
    .status-deploying {
        color: #ff6b35;
        font-weight: 600;
    }
    
    /* Chart containers - infrastructure monitoring style */
    [data-testid="stPlotlyContainer"] {
        border-radius: 8px;
        background: white;
        padding: 16px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(255, 107, 53, 0.1);
    }
    
    /* Dividers - DevOps themed */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(255, 107, 53, 0.3), transparent);
        margin: 24px 0;
    }
    
    /* Text styling */
    p, span, label {
        color: #333;
        line-height: 1.6;
    }
    
    /* Info boxes - infrastructure alerts */
    [data-testid="stAlert"] {
        border-radius: 8px;
        border-left: 4px solid #ff6b35;
    }
    
    /* Code blocks - terminal style */
    code {
        background: #1a1a1a;
        color: #00aa44;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
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
        st.markdown("## HemoStat Container Health Monitoring")
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
        ["🏥 Health Grid", "⚠️ Active Issues", "📊 History", "📈 Timeline"]
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
