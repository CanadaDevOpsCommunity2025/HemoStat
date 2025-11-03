"""
HemoStat Agents Package

Provides all four agent implementations for the HemoStat autonomous container health
monitoring system:

- **Monitor Agent**: Continuously polls Docker containers for health issues
- **Analyzer Agent**: Performs AI-powered root cause analysis
- **Responder Agent**: Executes safe remediation actions with safety constraints
- **Alert Agent**: Sends notifications and stores events for dashboard consumption

All agents inherit from HemoStatAgent base class and communicate via Redis pub/sub.
"""
