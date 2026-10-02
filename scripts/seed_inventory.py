"""Ejecutar explícitamente sobre desarrollo con un usuario autorizado."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/api'))
from dotenv import load_dotenv
load_dotenv(ROOT / 'services/api/.env')
load_dotenv(ROOT / '.env')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner-id', type=int, required=True)
    parser.add_argument('--development', action='store_true', required=True)
    args = parser.parse_args()
    from database import users_table
    from inventory.permissions import capabilities
    if not users_table.get(doc_id=args.owner_id) or not {'inventory:read','inventory:write'} <= capabilities(str(args.owner_id)):
        parser.error('El usuario debe existir y tener lectura y escritura de inventario.')
    from sqlmodel import Session
    from inventory.database import get_engine
    from inventory.seed import seed
    try:
        with Session(get_engine(), expire_on_commit=False) as session:
            applied = seed(session, str(args.owner_id))
        print('Semilla aplicada.' if applied else 'Semilla ya aplicada; sin duplicados.')
    except Exception:
        print('No se aplicó la semilla. Comprueba configuración, migración y coherencia de los SKU.', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
