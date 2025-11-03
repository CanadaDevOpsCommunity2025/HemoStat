# HemoStat Dashboard

Real-time Streamlit dashboard for monitoring HemoStat container health system. Displays live container metrics, active issues, remediation history, and event timeline.

## Overview

The HemoStat Dashboard provides a comprehensive real-time visualization of the entire HemoStat system, enabling operators to monitor container health, track remediation actions, and respond to issues quickly.

### Key Features

- **Real-time Container Health Grid** - Live status, CPU/memory metrics for all monitored containers
- **Active Issues Feed** - Failed/rejected remediations and recent health alerts with severity indicators
- **Remediation History** - Complete audit trail of all remediation attempts with filtering and sorting
- **Event Timeline** - Chronological view of all system events (health alerts, remediations, false alarms)
- **Auto-refresh** - Updates every 5 seconds (configurable) for real-time monitoring
- **Metrics Cards** - Key system metrics at a glance (total remediations, success rate, false alarms, active containers)
- **Responsive UI** - Streamlit-based responsive design with tabs for efficient navigation

## Architecture

The dashboard is built with modern Streamlit best practices:

- **Streamlit 1.51.0** - Web UI framework with reactive components, fragments, and bordered containers
- **Redis Integration** - Reads from `hemostat:events:*` and `hemostat:stats:*` keys
- **Efficient Caching** - Uses `@st.cache_data(ttl=5)` for 5-second Redis polling cache
- **Auto-refresh Fragments** - Uses `@st.fragment(run_every=N)` for partial page updates with dynamic intervals
- **HemoStatLogger** - Consistent logging with agents
- **Read-only Access** - No pub/sub subscription, polling-based for simplicity

## Configuration

### Environment Variables

All configuration is managed through environment variables in `.env`:

```bash
# Redis Configuration
REDIS_HOST=redis              # Redis server hostname (default: redis)
REDIS_PORT=6379              # Redis port (default: 6379)
REDIS_DB=0                    # Redis database number (default: 0)
REDIS_PASSWORD=               # Redis password (optional)

# Dashboard Configuration
DASHBOARD_PORT=8501           # Streamlit port (default: 8501)
DASHBOARD_REFRESH_INTERVAL=5  # Auto-refresh interval in seconds (default: 5)
DASHBOARD_MAX_EVENTS=100      # Maximum events to display (default: 100)
DASHBOARD_AUTO_REFRESH=true   # Enable auto-refresh by default (default: true)

# Logging
LOG_LEVEL=INFO                # Log level (DEBUG, INFO, WARNING, ERROR)
LOG_FORMAT=text               # Log format (text or json)
```

### Configuration Notes

- **Refresh Interval**: Lower values (1-2s) increase Redis load but provide faster updates. Higher values (10-30s) reduce load but delay updates.
- **Max Events**: Controls memory usage and rendering performance. Increase for more historical data, decrease for better performance.
- **Auto-refresh**: Can be toggled in the dashboard UI sidebar even if enabled by default.

## Usage

### Docker Compose (Recommended)

```bash
# Start all services including dashboard
docker-compose up -d

# Access dashboard at http://localhost:8501

# View logs
docker-compose logs -f dashboard

# Stop dashboard
docker-compose stop dashboard
```

### Local Development

```bash
# Install dependencies with UV
uv sync --extra dashboard

# Run dashboard
uv run streamlit run dashboard/app.py

# Or directly with streamlit
streamlit run dashboard/app.py
```

### Accessing the Dashboard

1. Open browser to `http://localhost:8501`
2. Dashboard auto-refreshes every 5 seconds (configurable in sidebar)
3. Use sidebar controls to:
   - Toggle auto-refresh on/off
   - Adjust refresh interval (1-60 seconds)
   - Click "Refresh Now" for manual refresh
4. Navigate tabs to view different dashboard sections

## Features in Detail

### Metrics Cards

Four key metrics displayed at the top:

- **Total Remediations** - Cumulative count of all remediation attempts
- **Success Rate** - Percentage of successful remediations (color-coded: green >80%, yellow 50-80%, red <50%)
- **False Alarms** - Count of false alarm events
- **Active Containers** - Number of containers currently being monitored

### Health Grid Tab

Real-time container health status table:

- **Container** - Container name/ID
- **Status** - Current health status (HEALTHY, UNHEALTHY, REMEDIATED)
- **CPU %** - Current CPU usage percentage
- **Memory %** - Current memory usage percentage
- **Last Update** - Relative timestamp of last update

### Active Issues Tab

Current problems requiring attention:

- **Failed Remediations** - Actions that failed to execute
- **Rejected Remediations** - Actions rejected due to cooldown/circuit breaker
- **Recent Health Alerts** - Unhealthy containers detected in last 5 minutes
- **Severity Indicators** - 🔴 critical, 🟡 high, 🟢 medium, ⚪ low
- **Expandable Details** - Click to see full error messages and details

### History Tab

Complete audit trail of remediation attempts:

- **Filters** - By status (All/Success/Failed/Rejected), container, time range
- **Columns** - Timestamp, Container, Action, Status, Reason, Confidence
- **Sortable** - Click column headers to sort
- **Color-coded** - Status column uses color coding for quick scanning

### Timeline Tab

Chronological view of all events:

- **Event Icons** - 🔍 health_alert, 🤖 remediation, ⚠️ false_alarm
- **Reverse Chronological** - Newest events first
- **Expandable Details** - Click to see full event JSON
- **Load More** - Limited to 100 most recent events for performance

## Troubleshooting

### "Cannot connect to Redis"

- Verify Redis service is running: `docker-compose ps redis`
- Check `REDIS_HOST` and `REDIS_PORT` in `.env`
- Test connection: `redis-cli -h <REDIS_HOST> -p <REDIS_PORT> ping`
- Ensure network connectivity between dashboard and Redis

### "No data displayed"

- Verify agents are running and publishing events
- Check Redis keys exist: `redis-cli KEYS 'hemostat:*'`
- Verify TTL hasn't expired on events: `redis-cli TTL hemostat:events:all`
- Check dashboard logs: `docker-compose logs dashboard`

### "Dashboard not refreshing"

- Check auto-refresh is enabled in sidebar
- Verify `DASHBOARD_REFRESH_INTERVAL` is set in `.env`
- Check browser console for JavaScript errors (F12)
- Try manual refresh with "Refresh Now" button

### "Port 8501 already in use"

- Change `DASHBOARD_PORT` in `.env` to an available port
- Or stop other Streamlit instances: `pkill -f streamlit`

### "Slow performance"

- Reduce `DASHBOARD_REFRESH_INTERVAL` (fewer updates)
- Reduce `DASHBOARD_MAX_EVENTS` (fewer events to render)
- Check Redis connection latency
- Increase cache TTL in `data_fetcher.py`

### "Import errors"

- Ensure `uv sync --extra dashboard` was run
- Verify `PYTHONPATH` includes project root
- Check Python version is 3.11+: `python --version`

## Development

### Adding New Components

1. Create new function in `components.py` following naming convention `render_*`
2. Use Google-style docstrings with Args/Returns sections
3. Import and call from `app.py` in appropriate tab or section
4. Test with sample data

### Adding New Data Sources

1. Create new function in `data_fetcher.py` following naming convention `get_*`
2. Decorate with `@st.cache_data(ttl=5)` for 5-second cache
3. Include error handling and logging
4. Import and call from `components.py` or `app.py`

### Customizing Styling

Streamlit theming can be customized via `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#36a64f"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### Adding New Tabs

1. Add new tab in `render_live_content()` function in `app.py`
2. Create corresponding component function in `components.py`
3. Fetch necessary data in `app.py` before rendering
4. Update tab labels and icons as needed

## Dependencies

All dependencies are managed via UV and `pyproject.toml`:

### Runtime Dependencies

- `streamlit==1.29.0` - Web UI framework
- `redis==5.0.1` - Redis client (from base dependencies)
- `python-dotenv==1.0.0` - Environment loading (from base dependencies)
- `python-json-logger==2.0.7` - Structured logging (from base dependencies)

### Installation

```bash
# Install with dashboard extra
uv sync --extra dashboard

# Install all extras (agents, dashboard, dev tools)
uv sync --all-extras
```

## Next Steps

The HemoStat Dashboard (Phase 3) is now complete. Next phases include:

- **Phase 4: Testing & Optimization** - Comprehensive test suite, performance profiling, production deployment guide
- **Integration Testing** - End-to-end tests with all agents running
- **Demo Scripts** - Sample scenarios and test data generation

## Screenshots

[Placeholder for dashboard screenshots]

- Dashboard overview with metrics cards
- Health grid view with container status
- Active issues feed with severity indicators
- Remediation history with filters
- Event timeline with chronological events

## Support

For issues, questions, or contributions:

- Check [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) for common issues
- Review [API_PROTOCOL.md](../docs/API_PROTOCOL.md) for Redis schema details
- See main [README.md](../README.md) for project overview
