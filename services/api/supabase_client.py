from functools import lru_cache

from supabase import Client, create_client

import config


@lru_cache
def get_supabase_client() -> Client:
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
