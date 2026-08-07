from pathlib import Path

from tinydb import TinyDB

DB_PATH = Path(__file__).parent / "db.json"

db = TinyDB(DB_PATH)
suppliers_table = db.table("suppliers")
