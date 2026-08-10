import os
from pathlib import Path

from tinydb import TinyDB

DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent / "db.json")))

db = TinyDB(DB_PATH)
suppliers_table = db.table("suppliers")
users_table = db.table("users")
password_reset_tokens_table = db.table("password_reset_tokens")
