"""Pytest configuration for integration tests.

This conftest manages sys.path and module caching to ensure proper imports
when running gateway and tenant-service tests together.

The key to avoiding conflicts:
1. Each test file sets up its own paths in a function-scoped fixture
2. Module clearing happens in the same fixture, not at module import time
3. No session-scoped fixtures that import service modules
"""

import sys
import importlib
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='[%(name)s] %(message)s')
logger = logging.getLogger('CONFTEST')

# Track which service paths have been added
_SERVICE_PATHS = {
    "gateway": "/home/mali/voice-ai-platform/services/gateway",
    "tenant": "/home/mali/voice-ai-platform/services/tenant-service",
}
SHARED_PATH = "/home/mali/voice-ai-platform/shared"
ROOT_PATH = "/home/mali/voice-ai-platform"


def _remove_all_service_paths():
    """Remove all service paths from sys.path."""
    for path in _SERVICE_PATHS.values():
        if path in sys.path:
            sys.path.remove(path)


def _add_gateway_paths():
    """Add gateway paths for gateway tests.

    Order matters! Insert in reverse order so first item is at position 0.
    """
    _remove_all_service_paths()
    if ROOT_PATH not in sys.path:
        sys.path.insert(0, ROOT_PATH)
    if SHARED_PATH not in sys.path:
        sys.path.insert(0, SHARED_PATH)
    if _SERVICE_PATHS["gateway"] not in sys.path:
        sys.path.insert(0, _SERVICE_PATHS["gateway"])


def _add_tenant_paths():
    """Add tenant-service paths for tenant-service tests.

    Order matters! Insert in reverse order so first item is at position 0.
    """
    _remove_all_service_paths()
    if ROOT_PATH not in sys.path:
        sys.path.insert(0, ROOT_PATH)
    if SHARED_PATH not in sys.path:
        sys.path.insert(0, SHARED_PATH)
    if _SERVICE_PATHS["tenant"] not in sys.path:
        sys.path.insert(0, _SERVICE_PATHS["tenant"])


def set_service_paths(service_name: str) -> None:
    """Set up paths for a specific service.

    Args:
        service_name: "gateway" or "tenant"
    """
    logger.info("set_service_paths(%s) called", service_name)
    logger.info("sys.path[:5] before: %s", sys.path[:5])

    if service_name == "gateway":
        _add_gateway_paths()
    elif service_name == "tenant":
        _add_tenant_paths()
    else:
        raise ValueError(f"Unknown service: {service_name}")

    logger.info("sys.path[:5] after: %s", sys.path[:5])


def clear_service_modules() -> None:
    """Clear service modules from cache to avoid import conflicts.

    This clears both 'app' and 'main' modules from sys.modules
    to prevent import conflicts between gateway and tenant-service tests.
    """
    logger.info("clear_service_modules() called")

    # Get list of modules to clear before modifying sys.modules
    modules_to_clear = []
    for mod_name in list(sys.modules.keys()):
        # Clear gateway's app.* modules (has routers, middleware, etc.)
        if mod_name.startswith("app.") or mod_name == "app":
            modules_to_clear.append(mod_name)
        # Clear tenant-service's app.* modules
        if mod_name.startswith("app.routers"):
            modules_to_clear.append(mod_name)
        if mod_name.startswith("app.models"):
            modules_to_clear.append(mod_name)
        if mod_name.startswith("app.services"):
            modules_to_clear.append(mod_name)
        if mod_name.startswith("app.jobs"):
            modules_to_clear.append(mod_name)
        # Clear main module
        if mod_name == "main" or mod_name.startswith("main."):
            modules_to_clear.append(mod_name)

    for mod_name in modules_to_clear:
        if mod_name in sys.modules:
            del sys.modules[mod_name]

    logger.info("Cleared %d modules", len(modules_to_clear))

    # Clear importlib caches
    importlib.invalidate_caches()


# Clean up at module unconfigure time
def pytest_unconfigure(config) -> None:
    """Restore initial sys.path."""
    _remove_all_service_paths()
    for path in [SHARED_PATH, ROOT_PATH]:
        if path in sys.path:
            sys.path.remove(path)
