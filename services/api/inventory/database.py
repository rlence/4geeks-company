"""Conexión diferida: sin configuración, inventario devuelve 503, otras rutas siguen disponibles."""
import os
from functools import lru_cache
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine
from .errors import unavailable


def make_engine(url: str):
    try:
        parsed = make_url(url)
        if parsed.get_backend_name() not in ('postgresql', 'postgres'):
            raise ValueError('PostgreSQL required')
        if not parsed.username or parsed.username.split('.')[0] != 'inventory_app':
            raise ValueError('Use the restricted inventory_app role')
        if parsed.host not in ('localhost', '127.0.0.1', '::1'):
            sslmode = parsed.query.get('sslmode', 'require')
            if sslmode not in ('require', 'verify-ca', 'verify-full'):
                raise ValueError('TLS required')
            parsed = parsed.update_query_dict({'sslmode': sslmode})
        parsed = parsed.set(drivername='postgresql+psycopg')
        return create_engine(parsed, isolation_level='READ COMMITTED', pool_pre_ping=True,
                             pool_size=5, max_overflow=5, pool_timeout=5, hide_parameters=True,
                             connect_args={'connect_timeout': 5, 'prepare_threshold': None})
    except Exception:
        raise unavailable() from None


@lru_cache(maxsize=1)
def get_engine():
    url = os.environ.get('INVENTORY_DATABASE_URL')
    if not url:
        raise unavailable()
    return make_engine(url)


def close_engine():
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()


def set_limits(session: Session):
    session.execute(text("SET LOCAL lock_timeout = '3s'"))
    session.execute(text("SET LOCAL statement_timeout = '5s'"))


def get_session():
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
