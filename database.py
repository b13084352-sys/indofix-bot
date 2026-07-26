import aiosqlite
import logging
from datetime import datetime

DB_PATH = "indofix_mvp.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                client_username TEXT,
                main_category TEXT,
                sub_category TEXT,
                description TEXT,
                location TEXT,
                desired_time TEXT,
                contacts TEXT,
                status TEXT DEFAULT 'new',
                worker_id INTEGER DEFAULT NULL,
                worker_username TEXT DEFAULT NULL,
                created_at TEXT,
                rating INTEGER DEFAULT NULL
            )
        """)
        await db.commit()

async def set_user_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language = ?",
            (user_id, lang, lang)
        )
        await db.commit()

async def get_user_language(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "en"

async def create_request(client_id: int, client_username: str, main_cat: str, sub_cat: str, desc: str, loc: str, time_str: str, contacts: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await db.execute(
            """INSERT INTO requests 
               (client_id, client_username, main_category, sub_category, description, location, desired_time, contacts, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, client_username or "", main_cat, sub_cat, desc, loc, time_str, contacts, now)
        )
        await db.commit()
        return cursor.lastrowid

async def assign_request(request_id: int, worker_id: int, worker_username: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT status FROM requests WHERE request_id = ?", (request_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row[0] != 'new':
                return False

        await db.execute(
            "UPDATE requests SET status = 'assigned', worker_id = ?, worker_username = ? WHERE request_id = ?",
            (worker_id, worker_username or "", request_id)
        )
        await db.commit()
        return True

async def complete_request(request_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE requests SET status = 'completed' WHERE request_id = ?", (request_id,))
        await db.commit()
        async with db.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)) as cursor:
            return await cursor.fetchone()

async def set_rating(request_id: int, rating: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE requests SET rating = ? WHERE request_id = ?", (rating, request_id))
        await db.commit()

async def get_request(request_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)) as cursor:
            return await cursor.fetchone()

async def get_client_requests(client_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM requests WHERE client_id = ? ORDER BY request_id DESC LIMIT 5", (client_id,)) as cursor:
            return await cursor.fetchall()

async def get_worker_jobs(worker_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM requests WHERE worker_id = ? AND status = 'assigned'", (worker_id,)) as cursor:
            return await cursor.fetchall()

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END), AVG(rating) FROM requests") as cursor:
            total, completed, avg_rating = await cursor.fetchone()
            return {
                'total': total or 0,
                'completed': completed or 0,
                'avg_rating': round(avg_rating, 1) if avg_rating else "N/A"
            }
