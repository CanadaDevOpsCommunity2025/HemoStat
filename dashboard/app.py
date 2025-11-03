"""
HemoStat Dashboard Main Application

Real-time Streamlit dashboard for monitoring HemoStat container health system.
Displays live container metrics, active issues, remediation history, and event timeline
with auto-refresh every 5 seconds.
"""

import os
from datetime import datetime

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
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "auto_refresh_enabled" not in st.session_state:
    st.session_state.auto_refresh_enabled = True
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", 5))
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


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
    st.sidebar.title("🏥 HemoStat")

    # System status section
    st.sidebar.subheader("System Status")
    redis_connected = check_redis_connection()
    status_indicator = "🟢 Connected" if redis_connected else "🔴 Disconnected"
    st.sidebar.write(f"**Redis**: {status_indicator}")

    if st.session_state.last_refresh:
        st.sidebar.write(f"**Last Refresh**: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

    refresh_interval = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", 5))
    st.sidebar.write(f"**Refresh Interval**: {refresh_interval}s")

    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

    # Settings section
    st.sidebar.subheader("Settings")
    st.session_state.auto_refresh_enabled = st.sidebar.checkbox(
        "Auto-refresh enabled",
        value=st.session_state.auto_refresh_enabled,
    )

    st.session_state.refresh_interval = st.sidebar.slider(
        "Refresh interval (seconds)",
        min_value=1,
        max_value=60,
        value=st.session_state.refresh_interval,
        step=1,
    )

    st.sidebar.info(
        "Auto-refresh updates the dashboard every N seconds. Lower intervals increase Redis load."
    )

    # Links section
    st.sidebar.subheader("Resources")
    st.sidebar.markdown(
        """
    - [📖 Documentation](https://github.com/jondmarien/HemoStat-test)
    - [🐙 GitHub Repository](https://github.com/jondmarien/HemoStat-test)
    - [📋 API Protocol](./docs/API_PROTOCOL.md)
    """
    )


def render_header() -> None:
    """
    Render dashboard header with title and connection status.

    Displays main title, subtitle with current timestamp, and
    connection status indicator.
    """
    st.title("🏥 HemoStat: Container Health Monitoring")
    st.markdown(f"Real-time monitoring dashboard | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Connection status
    redis_connected = check_redis_connection()
    if redis_connected:
        st.success("✅ Connected to Redis")
    else:
        st.error("❌ Cannot connect to Redis")


@st.fragment(run_every=5)  # type: ignore[attr-defined]
def render_live_content() -> None:
    """
    Render auto-refreshing dashboard content.

    This fragment updates every 5 seconds when auto-refresh is enabled.
    Fetches data from Redis and renders all dashboard tabs.
    """
    if not st.session_state.auto_refresh_enabled:
        st.info("Auto-refresh is disabled. Click 'Refresh Now' to update.")
        return

    st.session_state.last_refresh = datetime.now()

    try:
        # Fetch data
        with st.spinner("Loading data from Redis..."):
            all_events = get_all_events(limit=100)
            remediation_events = get_events_by_type("remediation_complete", limit=100)
            false_alarm_count = get_false_alarm_count()
            active_containers = len(get_active_containers())
            remediation_stats = get_remediation_stats()

        # Metrics section
        st.subheader("Key Metrics")
        render_metrics_cards(remediation_stats, false_alarm_count, active_containers)

        # Tabs for different views
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
            render_timeline(all_events)

    except Exception as e:
        logger.error(f"Error rendering dashboard content: {e}")
        st.error(f"Error loading dashboard data: {e}")


def render_footer() -> None:
    """
    Render dashboard footer with version and status information.

    Displays HemoStat version, agent status summary, and last update timestamp.
    """
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("HemoStat v1.0.0")

    with col2:
        st.caption("Phase 3: Dashboard & Visualization")

    with col3:
        if st.session_state.last_refresh:
            st.caption(f"Last updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}")


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
