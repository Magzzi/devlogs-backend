# Supabase client (service-role) — used by repositories
from functools import lru_cache
from supabase import create_client, Client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a lazily-created, cached Supabase service-role client."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
