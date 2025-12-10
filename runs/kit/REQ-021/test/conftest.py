"""
Pytest configuration for REQ-021 tests.

REQ-021: Observability instrumentation
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def reset_observability_state():
    """Reset global observability state between tests."""
    # Reset config
    import infra.observability.config as config_module
    config_module._config = None
    
    # Reset metrics registry
    import infra.observability.metrics as metrics_module
    metrics_module._registry = None
    
    # Reset tracer
    import infra.observability.tracing as tracing_module
    tracing_module._tracer = None
    
    # Reset health checker
    import infra.observability.health as health_module
    health_module._health_checker = None
    
    # Reset loggers
    import infra.observability.logging as logging_module
    logging_module._loggers.clear()
    
    yield