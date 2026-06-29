"""Lazy Supabase client singleton.

Returns None (never raises) when SUPABASE_URL / SUPABASE_SERVICE_KEY are absent
or the client can't be built, so callers can treat the DB as optional.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv absent — env may still be set by the host
    pass

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_client():
    """Return a cached Supabase client, or None if it can't be configured."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        log.warning("Supabase not configured — DB mirror disabled.")
        return None
    try:
        from supabase import create_client

        return create_client(url, key)
    except Exception as exc:  # missing package, bad creds, etc.
        log.warning("Could not initialise Supabase client: %s", exc)
        return None
