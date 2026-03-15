"""Pytest configuration for integration tests.

This conftest manages sys.path to ensure proper module imports when
running gateway and tenant-service tests together.
"""

import sys
import importlib

print("[CONFTEST] Module loaded, sys.path[:3] =", sys.path[:3])

# Track which service paths have been added
_service_paths = {
    "gateway": "/home/mali/voice-ai-platform/services/gateway",
    "tenant": "/home/mali/voice-ai-platform/services/tenant-service",
}
SHARED_PATH = "/home/mali/voice-ai-platform/shared"
ROOT_PATH = "/home/mali/voice-ai-platform"


def _remove_all_service_paths():
    """Remove all service paths from sys.path."""
    for path in _service_paths.values():
        if path in sys.path:
            sys.path.remove(path)


def _add_gateway_paths():
    """Add gateway paths for gateway tests."""
    _remove_all_service_paths()
    if _service_paths["gateway"] not in sys.path:
        sys.path.insert(0, _service_paths["gateway"])
    if SHARED_PATH not in sys.path:
        sys.path.insert(0, SHARED_PATH)
    if ROOT_PATH not in sys.path:
        sys.path.insert(0, ROOT_PATH)


def _add_tenant_paths():
    """Add tenant-service paths for tenant-service tests."""
    _remove_all_service_paths()
    if _service_paths["tenant"] not in sys.path:
        sys.path.insert(0, _service_paths["tenant"])
    if SHARED_PATH not in sys.path:
        sys.path.insert(0, SHARED_PATH)
    if ROOT_PATH not in sys.path:
        sys.path.insert(0, ROOT_PATH)


# Track which service paths are currently active
_current_service = None


def pytest_configure(config):
    """Store initial sys.path and setup path tracking."""
    config._initial_sys_path = list(sys.path)


def pytest_unconfigure(config):
    """Restore initial sys.path."""
    if hasattr(config, "_initial_sys_path"):
        # Remove any service paths we might have added
        _remove_all_service_paths()
        for path in [SHARED_PATH, ROOT_PATH]:
            if path in sys.path:
                sys.path.remove(path)
        # Restore original paths
        for path in reversed(config._initial_sys_path):
            if path not in sys.path:
                sys.path.insert(0, path)


def set_service_paths(service_name):
    """Set up paths for a specific service.

    Args:
        service_name: "gateway" or "tenant"
    """
    global _current_service

    print(f"[CONFTEST] set_service_paths({service_name}) called")
    print(f"[CONFTEST] sys.path[:5] before: {sys.path[:5]}")

    if service_name == "gateway":
        _add_gateway_paths()
    elif service_name == "tenant":
        _add_tenant_paths()
    else:
        raise ValueError(f"Unknown service: {service_name}")

    print(f"[CONFTEST] sys.path[:5] after: {sys.path[:5]}")
    _current_service = service_name


def clear_service_modules():
    """Clear service modules from cache to avoid import conflicts.

    This function clears both 'app' and 'main' modules from sys.modules
    to prevent import conflicts between gateway and tenant-service tests.
    """
    print(f"[CONFTEST] clear_service_modules() called")
    app_modules_before = [m for m in sys.modules.keys() if m.startswith("app.") or m == "app" or m == "main"]
    print(f"[CONFTEST] App modules before: {app_modules_before}")

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

    app_modules_after = [m for m in sys.modules.keys() if m.startswith("app.") or m == "app" or m == "main"]
    print(f"[CONFTEST] App modules after: {app_modules_after}")

    # Clear importlib caches
    importlib.invalidate_caches()
