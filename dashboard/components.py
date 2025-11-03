"""
Dashboard UI Components Module

Provides reusable Streamlit components for rendering dashboard visualizations.
Includes metrics cards, health grids, issue feeds, history tables, and timelines.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from agents.logger import HemoStatLogger
from dashboard.data_fetcher import get_all_container_stats


def render_metrics_cards(
    remediation_stats: dict[str, Any], false_alarm_count: int, active_containers: int
) -> None:
    """
    Render key metrics in a row of cards.

    Displays four metric cards showing total remediations, success rate,
    false alarms, and active containers. Uses color coding for success rate
    (green >80%, yellow 50-80%, red <50%).

    Args:
        remediation_stats: Dictionary with remediation statistics
        false_alarm_count: Number of false alarm events
        active_containers: Number of active containers
    """
    col1, col2, col3, col4 = st.columns(4, gap="medium")

    with col1:
        st.metric(
            label="Total Remediations",
            value=remediation_stats.get("total", 0),
            delta=None,
        )

    with col2:
        success_rate = remediation_stats.get("success_rate", 0.0)
        # Determine delta color based on success rate
        if success_rate >= 80:
            delta_color = "off"  # Green
        elif success_rate >= 50:
            delta_color = "off"  # Yellow
        else:
            delta_color = "inverse"  # Red

        st.metric(
            label="Success Rate",
            value=f"{success_rate:.1f}%",
            delta=None,
            delta_color=delta_color,
        )

    with col3:
        st.metric(
            label="False Alarms",
            value=false_alarm_count,
            delta=None,
        )

    with col4:
        st.metric(
            label="Active Containers",
            value=active_containers,
            delta=None,
        )


def render_health_grid(events: list[dict]) -> None:
    """
    Render container health status in a grid layout.

    Displays a table of containers with their latest status, CPU/memory
    percentages from `hemostat:stats:*` keys (preferred) or event data (fallback),
    and last update timestamp. Uses color coding for status
    (green=healthy, red=unhealthy, blue=remediated).

    Args:
        events: List of event dictionaries from Redis
    """
    if not events:
        st.info("No containers monitored yet")
        return

    # Extract unique containers from recent events
    containers_map = {}
    for event in events:
        # Extract container from nested data structure
        data = event.get("data", {})
        container_name = data.get("container")
        if container_name and container_name not in containers_map:
            containers_map[container_name] = event

    if not containers_map:
        st.info("No container data available")
        return

    # Fetch container stats from hemostat:stats:* keys
    all_stats = get_all_container_stats()

    # Build dataframe for display
    grid_data = []
    for container_name, event in containers_map.items():
        # Extract data from event
        data = event.get("data", {})
        result = data.get("result", {})
        
        # Prefer stats from hemostat:stats:*, fall back to event data
        stats = all_stats.get(container_name, {})
        cpu_percent = stats.get("cpu_percent", data.get("cpu_percent", 0))
        memory_percent = stats.get("memory_percent", data.get("memory_percent", 0))
        status = result.get("status", stats.get("status", "active")).upper()
        timestamp = event.get("timestamp", stats.get("timestamp", ""))

        grid_data.append(
            {
                "Container": container_name,
                "Status": status,
                "CPU %": f"{cpu_percent:.1f}",
                "Memory %": f"{memory_percent:.1f}",
                "Last Update": format_timestamp(timestamp),
            }
        )

    st.dataframe(
        grid_data,
        width="stretch",
        hide_index=True,
    )


def render_active_issues(events: list[dict]) -> None:
    """
    Render active issues that need attention.

    Displays failed/rejected remediations and recent health alerts with
    severity indicators. Uses expanders for detailed information.

    Args:
        events: List of event dictionaries from Redis
    """
    logger = HemoStatLogger.get_logger("dashboard")

    # Filter for active issues
    active_issues = []
    now = datetime.now(UTC)
    five_minutes_ago = now - timedelta(minutes=5)

    for event in events:
        status = event.get("status", "").lower()
        timestamp_str = event.get("timestamp", "")

        # Include failed/rejected remediations
        if status in ["failed", "rejected"]:
            active_issues.append(event)
        # Include recent health alerts
        elif status == "unhealthy":
            try:
                event_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if event_time > five_minutes_ago:
                    active_issues.append(event)
            except (ValueError, AttributeError):
                logger.warning(f"Invalid timestamp format: {timestamp_str}")

    if not active_issues:
        st.info("No active issues")
        return

    for issue in active_issues:
        container_id = issue.get("container_id", "Unknown")
        status = issue.get("status", "unknown").upper()
        severity = get_severity_emoji(issue.get("severity", "unknown"))

        with st.expander(f"{severity} {container_id} - {status}", expanded=False):
            st.write(f"**Container**: {container_id}")
            st.write(f"**Status**: {status}")
            st.write(f"**Reason**: {issue.get('reason', 'N/A')}")
            st.write(f"**Timestamp**: {format_timestamp(issue.get('timestamp', ''))}")
            if issue.get("error_message"):
                st.error(f"Error: {issue.get('error_message')}")


def render_remediation_history(events: list[dict]) -> None:
    """
    Render table of remediation attempts with filtering.

    Displays all remediation events with columns for timestamp, container,
    action, status, reason, and confidence. Includes filters for status,
    container, and time range. Reasons can be expanded to view full text.

    Args:
        events: List of remediation event dictionaries from Redis
    """
    if not events:
        st.info("No remediation history available")
        return

    # Create filter columns
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Success", "Failed", "Rejected"],
            key="status_filter",
        )

    with col2:
        unique_containers = sorted({e.get("data", {}).get("container", "Unknown") for e in events})
        container_filter = st.selectbox(
            "Filter by Container",
            ["All", *unique_containers],
            key="container_filter",
        )

    with col3:
        time_filter = st.selectbox(
            "Filter by Time Range",
            ["Last hour", "Last 24h", "Last 7d", "All"],
            key="time_filter",
        )

    # Apply filters
    filtered_events = events
    now = datetime.now(UTC)

    if status_filter != "All":
        status_map = {
            "Success": "success",
            "Failed": "failed",
            "Rejected": "rejected",
        }
        filtered_events = [
            e
            for e in filtered_events
            if e.get("data", {}).get("result", {}).get("status", "").lower() == status_map.get(status_filter, "")
        ]

    if container_filter != "All":
        filtered_events = [e for e in filtered_events if e.get("data", {}).get("container") == container_filter]

    if time_filter != "All":
        time_deltas = {
            "Last hour": timedelta(hours=1),
            "Last 24h": timedelta(hours=24),
            "Last 7d": timedelta(days=7),
        }
        cutoff_time = now - time_deltas.get(time_filter, timedelta(days=7))

        filtered_events_with_time = []
        for event in filtered_events:
            try:
                event_time = datetime.fromisoformat(
                    event.get("timestamp", "").replace("Z", "+00:00")
                )
                if event_time > cutoff_time:
                    filtered_events_with_time.append(event)
            except (ValueError, AttributeError):
                filtered_events_with_time.append(event)
        filtered_events = filtered_events_with_time

    # Build dataframe
    history_data = []
    full_reasons_map = {}  # Map to store full reasons separately
    
    for idx, event in enumerate(filtered_events):
        # Extract data from nested structure
        data = event.get("data", {})
        result = data.get("result", {})
        
        # Get reason from result (remediation reason) or data (AI analysis reason)
        full_reason = result.get("reason") or data.get("reason") or "N/A"
        
        # Truncate for display (no forced ellipsis)
        max_display_length = 60
        if len(str(full_reason)) > max_display_length:
            display_reason = str(full_reason)[:max_display_length]
        else:
            display_reason = str(full_reason)
        
        row_key = f"{idx}_{data.get('container', 'Unknown')}"
        full_reasons_map[row_key] = {
            "full_reason": full_reason,
            "container": data.get("container", "Unknown"),
            "timestamp": format_timestamp(event.get("timestamp", "")),
        }
        
        history_data.append(
            {
                "Timestamp": format_timestamp(event.get("timestamp", "")),
                "Container": data.get("container", "Unknown"),
                "Action": data.get("action", "Unknown"),
                "Status": result.get("status", "unknown").upper(),
                "Reason": display_reason,
                "Confidence": f"{data.get('confidence', 0):.1%}",
            }
        )

    st.dataframe(
        history_data,
        width="stretch",
        hide_index=True,
    )
    
    # Add expandable sections for full reasons
    st.markdown("---")
    st.subheader("📋 Full Reasoning Details")
    
    for row_key, reason_data in full_reasons_map.items():
        if len(str(reason_data["full_reason"])) > 60:
            with st.expander(f"{reason_data['container']} - {reason_data['timestamp']}", expanded=False):
                st.write(reason_data["full_reason"])


def render_timeline(events: list[dict], max_events: int = 100) -> None:
    """
    Render chronological timeline of all events with graph visualization.

    Displays events in reverse chronological order (newest first) with
    type indicators, container names, and expandable details. Also shows
    a timeline graph of event frequency.

    Args:
        events: List of event dictionaries from Redis
        max_events: Maximum number of events to display (default: 100)
    """
    if not events:
        st.info("No events to display")
        return

    # Sort by timestamp, newest first
    sorted_events = sorted(events, key=lambda x: x.get("timestamp", ""), reverse=True)

    # Build event type counts for graph
    event_type_counts = {}
    for event in sorted_events:
        event_type = event.get("event_type", "unknown").lower()
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

    # Display event type distribution chart
    st.markdown("**Event Type Distribution**")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        import altair as alt
        df = pd.DataFrame(list(event_type_counts.items()), columns=["Event Type", "Count"])
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Event Type:N", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Count:Q"),
            color=alt.value("#1f77b4"),
            tooltip=["Event Type", "Count"]
        ).properties(
            width="container",
            height=300
        )
        st.altair_chart(chart, use_container_width=True)
    with col3:
        st.metric("Total Events", len(sorted_events))

    st.markdown("---")
    st.markdown("**Recent Events**")

    # Display events
    for event in sorted_events[:max_events]:
        event_type = event.get("event_type", "unknown").lower()
        
        # Extract container from nested data structure
        data = event.get("data", {})
        container_id = data.get("container", event.get("container_id", "Unknown"))
        
        timestamp = format_timestamp(event.get("timestamp", ""))
        icon = get_event_type_icon(event_type)
        
        # Build description from event data
        description = ""
        if event_type == "remediation_complete":
            action = data.get("action", "unknown")
            result = data.get("result", {})
            status = result.get("status", "unknown")
            description = f"Action: {action} | Status: {status}"
        elif event_type == "health_alert":
            status = data.get("status", "unknown")
            description = f"Status: {status}"
        elif event_type == "false_alarm":
            reason = data.get("reason", "No reason provided")
            description = f"Reason: {reason[:60]}"
        else:
            description = event.get("description", "No description")

        with st.container(border=True):
            st.write(f"{icon} **{timestamp}** - {container_id}")
            st.caption(description if description else "No description")

            with st.expander("Details"):
                st.json(event)


def format_timestamp(iso_timestamp: str) -> str:
    """
    Format ISO timestamp to relative or absolute time string in Eastern Time (GMT-5).

    Converts ISO timestamps to relative time for recent events
    ("2 minutes ago", "1 hour ago") and absolute time for older events
    ("Jan 3, 10:30 AM EST").

    Args:
        iso_timestamp: ISO format timestamp string

    Returns:
        str: Formatted timestamp string in Eastern Time or "Unknown" if invalid
    """
    if not iso_timestamp:
        return "Unknown"

    try:
        # Parse timestamp and convert to Eastern Time
        eastern = ZoneInfo("America/New_York")
        event_time_utc = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        
        # Convert to Eastern Time
        if event_time_utc.tzinfo:
            event_time_et = event_time_utc.astimezone(eastern)
        else:
            # Assume UTC if no timezone
            event_time_et = event_time_utc.replace(tzinfo=UTC).astimezone(eastern)
        
        now_et = datetime.now(eastern)
        
        # Calculate delta using timezone-aware datetimes
        delta = now_et - event_time_et

        # Relative time for recent events
        if delta < timedelta(minutes=1):
            return "Just now"
        elif delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta < timedelta(days=7):
            days = int(delta.total_seconds() / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            # Absolute time for older events with timezone abbreviation
            tz_abbr = event_time_et.strftime("%Z")  # EST or EDT
            return event_time_et.strftime(f"%b %d, %I:%M %p {tz_abbr}")
    except (ValueError, AttributeError) as e:
        return "Unknown"


def get_status_color(status: str) -> str:
    """
    Map status string to hex color code.

    Returns color codes for different status values:
    - success/healthy: green
    - failed/unhealthy: red
    - rejected: orange
    - unknown: gray

    Args:
        status: Status string

    Returns:
        str: Hex color code
    """
    status_lower = status.lower()
    color_map = {
        "success": "#36a64f",
        "healthy": "#36a64f",
        "failed": "#ff0000",
        "unhealthy": "#ff0000",
        "rejected": "#ff9900",
        "unknown": "#cccccc",
    }
    return color_map.get(status_lower, "#cccccc")


def get_severity_emoji(severity: str) -> str:
    """
    Map severity level to text indicator.

    Returns text indicator for different severity levels:
    - critical: [CRITICAL]
    - high: [HIGH]
    - medium: [MEDIUM]
    - low: [LOW]
    - unknown: [UNKNOWN]

    Args:
        severity: Severity level string

    Returns:
        str: Text indicator
    """
    severity_lower = severity.lower()
    indicator_map = {
        "critical": "[CRITICAL]",
        "high": "[HIGH]",
        "medium": "[MEDIUM]",
        "low": "[LOW]",
        "unknown": "[UNKNOWN]",
    }
    return indicator_map.get(severity_lower, "[UNKNOWN]")


def get_event_type_icon(event_type: str) -> str:
    """
    Map event type to text indicator.

    Returns text indicator for different event types:
    - health_alert: [ALERT]
    - remediation: [REMEDIATION]
    - false_alarm: [FALSE ALARM]
    - unknown: [EVENT]

    Args:
        event_type: Event type string

    Returns:
        str: Text indicator
    """
    event_type_lower = event_type.lower()
    icon_map = {
        "health_alert": "[ALERT]",
        "remediation": "[REMEDIATION]",
        "false_alarm": "[FALSE ALARM]",
        "unknown": "[EVENT]",
    }
    return icon_map.get(event_type_lower, "[EVENT]")
