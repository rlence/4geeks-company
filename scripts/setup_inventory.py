"""Preparación explícita de desarrollo. Nunca imprime credenciales ni modifica .env."""
import argparse
from getpass import getpass
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
from dotenv import load_dotenv
load_dotenv(ROOT / 'services/api/.env')
load_dotenv(ROOT / '.env')
import psycopg
from psycopg import sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Aplicar la migración si no existe el esquema inventory.')
    parser.add_argument('--enable-login', action='store_true', help='Asignar contraseña a inventory_app mediante entrada oculta.')
    args = parser.parse_args()
    if not (args.apply or args.enable_login):parser.error('Indica --apply o --enable-login.')
    url = os.environ.get('INVENTORY_ADMIN_DATABASE_URL')
    if not url:parser.error('Configura INVENTORY_ADMIN_DATABASE_URL en el entorno del servidor.')
    password = None
    if args.enable_login:
        password = getpass('Contraseña nueva para inventory_app (mínimo 20 caracteres): ')
        if len(password) < 20 or password != getpass('Repite la contraseña: '):
            parser.error('La contraseña no coincide o es demasiado corta.')
    try:
        with psycopg.connect(url, connect_timeout=5) as conn:
            if args.apply:
                exists = conn.execute("SELECT 1 FROM pg_namespace WHERE nspname='inventory'").fetchone()
                if exists:
                    print('El esquema inventory ya existe. No se sobrescribe; revisa la migración aplicada.')
                else:
                    conn.execute((ROOT/'supabase/migrations/20261002012816_inventory_api.sql').read_text())
                    print('Migración preparada en la transacción.')
            flags = conn.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname='inventory_app'").fetchone()
            if flags is None or any(flags):
                raise ValueError('Rol de aplicación ausente o con privilegios incompatibles')
            if password:
                conn.execute(sql.SQL('ALTER ROLE inventory_app LOGIN PASSWORD {}').format(sql.Literal(password)))
        print('Preparación confirmada. Configura INVENTORY_DATABASE_URL con inventory_app y su contraseña; no uses el usuario administrador en la API.')
    except Exception:
        print('No se completó la preparación. Revisa conexión, permisos y esquema. No se imprimen detalles que puedan contener secretos.', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
