"""Admin data-access gateway.

Routes import this module instead of binding directly to the local-Postgres
implementation. In Supabase mode, admin/staff APIs use the Supabase REST client
and do not require DATABASE_URL or a local Postgres server.
"""

from __future__ import annotations

import os

from db import admin as postgres_admin
from db import admin_supabase

AdminDatabaseNotConfigured = postgres_admin.AdminDatabaseNotConfigured


def _backend():
    provider = os.environ.get("DATABASE_PROVIDER", "").strip().lower()
    if provider == "postgres":
        return postgres_admin
    return admin_supabase


def __getattr__(name: str):
    return getattr(_backend(), name)
