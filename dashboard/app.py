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


# Initialize session state
if "auto_refresh_enabled" not in st.session_state:
    auto_refresh_env = os.getenv("DASHBOARD_AUTO_REFRESH", "true").lower() == "true"
    st.session_state.auto_refresh_enabled = auto_refresh_env
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", 5))
if "max_events" not in st.session_state:
    st.session_state.max_events = int(os.getenv("DASHBOARD_MAX_EVENTS", 100))
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
    col1, col2 = st.columns([3, 1])
    eastern = ZoneInfo("America/New_York")
    now_et = datetime.now(eastern)
    tz_abbr = now_et.strftime("%Z")  # EST or EDT
    st.title("🏥 HemoStat: Container Health Monitoring")
    st.markdown(f"Real-time monitoring dashboard | {now_et.strftime(f'%Y-%m-%d %I:%M:%S %p {tz_abbr}')}")

    with col1:
        st.title("HemoStat")
        st.caption(f"Container Health Monitoring • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    with col2:
        redis_connected = check_redis_connection()
        status_text = "Redis Connected" if redis_connected else "Redis Disconnected"
        bg_color = "#d4edda" if redis_connected else "#f8d7da"
        text_color = "#155724" if redis_connected else "#721c24"
        st.markdown(
            f"<div style='text-align: right; margin-top: 1.5rem;'>"
            f"<span style='background-color: {bg_color}; color: {text_color}; "
            f"padding: 4px 12px; border-radius: 4px; font-weight: 600; font-size: 14px;'>"
            f"{status_text}</span></div>",
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
