import aiosqlite
import logging

DB_NAME = "cafe.db"
logger = logging.getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                date TEXT NOT NULL,
                guests INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                telegram_id INTEGER
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                photo_url TEXT,
                is_available INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.commit()


async def save_booking(name: str, phone: str, date: str, guests: int, telegram_id: int) -> int:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO bookings (name, phone, date, guests, telegram_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, phone, date, guests, telegram_id),
        )
        await db.commit()
        return cursor.lastrowid


async def update_booking_status(booking_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
        await db.commit()


async def get_booking_by_id(booking_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        row = await cursor.fetchone()
        return row


async def get_user_bookings(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT id, name, phone, date, guests, created_at, status
            FROM bookings
            WHERE telegram_id = ?
            ORDER BY created_at DESC
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return rows
