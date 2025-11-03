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
    page_icon="📊",
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
        st.sidebar.caption(f"Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S')}")

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
    """

    # Use fragment with conditional auto-refresh
    # Pass the manual_refresh_trigger to force re-render when button clicked
    refresh_interval = st.session_state.refresh_interval if st.session_state.auto_refresh_enabled else None

    @st.fragment(run_every=refresh_interval)  # type: ignore[attr-defined]
    def content_fragment() -> None:
        # This will cause re-render when manual_refresh_trigger changes
        _ = st.session_state.manual_refresh_trigger
        st.session_state.last_refresh = datetime.now()
        render_dashboard_content()

    content_fragment()


def render_dashboard_content() -> None:
    """
    Render the main dashboard content (metrics, tabs, etc).

    Separated from render_live_content to allow reuse with and without auto-refresh.
    """
    try:
        # Fetch data
        with st.spinner("Loading data from Redis..."):
            all_events = get_all_events(limit=st.session_state.max_events)
            remediation_events = get_events_by_type(
                "remediation_complete", limit=st.session_state.max_events
            )
            false_alarm_count = get_false_alarm_count()
            active_containers = len(get_active_containers())
            remediation_stats = get_remediation_stats()

        # Metrics section
        render_metrics_cards(remediation_stats, false_alarm_count, active_containers)

        # Add spacing
        st.markdown("<br>", unsafe_allow_html=True)

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Health Grid", "Active Issues", "History", "Timeline"]
        )

        with tab1:
            render_health_grid(all_events)

        with tab2:
            render_active_issues(all_events)

        with tab3:
            render_remediation_history(remediation_events)

        with tab4:
            render_timeline(all_events, max_events=st.session_state.max_events)

    except Exception as e:
        logger.error(f"Error rendering dashboard content: {e}")
        st.error(f"Error loading dashboard data: {e}")


def render_footer() -> None:
    """
    Render dashboard footer with version and status information.

    Displays HemoStat version and last update timestamp.
    """
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.caption("HemoStat v1.0.0")

    with col2:
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
