Agents Package
==============

All agent implementations and base classes. This documentation is auto-generated from Python docstrings.

Package Overview
----------------

.. automodule:: agents
   :members:
   :undoc-members:
   :show-inheritance:

Base Agent Class
----------------

Foundation for all agents. Provides Redis pub/sub communication and shared state management.

.. automodule:: agents.agent_base
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Logger
------

Logging utilities for all agents.

.. automodule:: agents.logger
   :members:
   :undoc-members:
   :show-inheritance:

Platform Utilities
------------------

Platform detection and utilities.

.. automodule:: agents.platform_utils
   :members:
   :undoc-members:
   :show-inheritance:

Monitor Agent
-------------

Continuously monitors Docker container health and publishes alerts.

.. automodule:: agents.hemostat_monitor.monitor
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Analyzer Agent
--------------

Performs AI-powered root cause analysis on health alerts.

.. automodule:: agents.hemostat_analyzer.analyzer
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Responder Agent
---------------

Executes safe remediation actions on containers.

.. automodule:: agents.hemostat_responder.responder
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Alert Agent
-----------

Sends notifications and stores event history.

.. automodule:: agents.hemostat_alert.alert
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__
