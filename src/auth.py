"""
Authentication module with demo credentials and token verification.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Optional, Dict, Any

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "settlement-agent-super-secret-key-2026")

DEMO_USERS = {
    "admin@settlementagent.ai": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "name": "Thaarunya Anantharaman",
        "role": "Lead Reconciliation Architect",
        "email": "admin@settlementagent.ai",
    },
    "demo@merchant.com": {
        "password_hash": hashlib.sha256("demo123".encode()).hexdigest(),
        "name": "Finance Operations",
        "role": "Financial Controller",
        "email": "demo@merchant.com",
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def create_access_token(email: str, expires_in_seconds: int = 86400 * 7) -> str:
    """Creates a signed session token."""
    expire_timestamp = int(time.time()) + expires_in_seconds
    payload = f"{email}:{expire_timestamp}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies a signed session token and returns user info if valid."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        email, expire_str, signature = parts
        expire_timestamp = int(expire_str)
        if time.time() > expire_timestamp:
            return None

        payload = f"{email}:{expire_timestamp}"
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        user = DEMO_USERS.get(email)
        if user:
            return {
                "email": user["email"],
                "name": user["name"],
                "role": user["role"],
            }
        # Generic authenticated user fallback
        return {
            "email": email,
            "name": email.split("@")[0].title(),
            "role": "Auditor",
        }
    except Exception:
        return None
