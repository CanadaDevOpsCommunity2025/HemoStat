API Reference
=============

Complete API documentation auto-generated from Python docstrings.

This section contains comprehensive documentation for all HemoStat classes, methods, and functions. All documentation is **automatically extracted from Google-style docstrings** in the Python code, ensuring it stays in sync with the implementation.

.. toctree::
   :maxdepth: 2
   :caption: API Modules:

   agents
   dashboard

Base Classes
============

All agents inherit from :class:`agents.agent_base.HemoStatAgent`, which provides:

- Redis pub/sub communication primitives
- Shared state management
- Graceful shutdown handling
- Connection retry logic with exponential backoff

See the :doc:`agents` section for complete documentation of the base class and all agent implementations.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
