import sqlite3
import json
import os
from pathlib import Path

# Create database directory if it doesn't exist
db_dir = Path("data")
db_dir.mkdir(exist_ok=True)

# Connect to SQLite
db_path = db_dir / "tasks.db"
def get_db():
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            status TEXT,
            output TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            query TEXT PRIMARY KEY,
            profiles TEXT
        )
    """)

class Task:
    @staticmethod
    def save(task_id, status, output=None):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tasks (id, status, output) VALUES (?, ?, ?)",
                (task_id, status, output if output is not None else '')
            )

    @staticmethod
    def get(task_id):
        with get_db() as conn:
            result = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(result) if result else {}

    @staticmethod
    def get_all_keys():
        with get_db() as conn:
            results = conn.execute("SELECT id FROM tasks").fetchall()
            return [result['id'] for result in results]

    @staticmethod
    def save_search_history(query: str, profiles: str):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO search_history (query, profiles) VALUES (?, ?)",
                (query, profiles)
            )

    @staticmethod
    def get_search_history(query: str):
        with get_db() as conn:
            result = conn.execute(
                "SELECT profiles FROM search_history WHERE query = ?",
                (query,)
            ).fetchone()
            return result['profiles'] if result else None