"""Cryptographic utilities for secure key generation."""

import secrets


def generate_secure_key() -> str:
    """Generate a secure 32-character hex string using secrets module.

    Returns:
        64-character hex string (32 bytes encoded as hex)
    """
    return secrets.token_hex(32)
