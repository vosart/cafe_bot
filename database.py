import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_NAME = "cafe.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    with get_db() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id           INTEGER PRIMARY     KEY AUTOINCREMENT,
                name         TEXT    NOT NULL,
                phone        TEXT    NOT NULL,
                date         TEXT    NOT NULL,
                guests       INTEGER NOT NULL,
                created_at   TEXT    DEFAULT     CURRENT_TIMESTAMP
            )                    
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                category        TEXT    NOT NULL,
                name            TEXT    NOT NULL,
                description     TEXT,
                price           REAL    NOT NULL,
                photo_url       TEXT,
                is_available    INTEGER DEFAULT 1,
                created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        try:
            cursor.execute(
                "ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'pending'"
            )
        except:  # pylint: disable=bare-except
            pass
        try:
            cursor.execute("ALTER TABLE bookings ADD COLUMN telegram_id INTEGER")
        except:
            pass


def save_booking(
    name: str, phone: str, date: str, guests: int, telegram_id: int
) -> int:
    with get_db() as cursor:
        cursor.execute(
            """
                    INSERT INTO bookings (name, phone, date, guests, telegram_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
            (name, phone, date, guests, telegram_id),
        )

        booking_id = cursor.lastrowid

        return booking_id


def update_booking_status(booking_id: int, status: str):
    with get_db() as cursor:
        cursor.execute(
            "UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id)
        )


def get_booking_by_id(booking_id: int):
    with get_db() as cursor:
        cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))

        return cursor.fetchone()


def get_all_bookings() -> list:
    with get_db() as cursor:
        cursor.execute("""
                    SELECT id, name, phone, date, guests, created_at, status
                    FROM bookings
                    ORDER BY created_at DESC
                    """)

        return cursor.fetchall()


# получить все брони пользователя по telegram_id
def get_user_bookings(telegram_id: int) -> list:
    with get_db() as cursor:
        cursor.execute(
            """
                    SELECT id, name, phone, date, guests, created_at, status
                    FROM bookings
                    WHERE telegram_id = ?
                    ORDER BY created_at DESC
                    """,
            (telegram_id,),
        )

        return cursor.fetchall()


def get_stats() -> dict:
    with get_db() as cursor:
        cursor.execute("SELECT COUNT(*) FROM bookings")
        total = cursor.fetchone()[0]

        cursor.execute("""
                    SELECT COUNT(*) FROM bookings
                    WHERE DATE(created_at) = Date('now')
                    """)
        today = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(guests) FROM bookings")
        total_guests = cursor.fetchone()[0] or 0

        return {"total": total, "today": today, "total_guests": total_guests}


# Получить все брони на завтра
def get_tomorrow_bookings() -> list:
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    with get_db() as cursor:
        cursor.execute(
            """
            SELECT id, name, phone, date, guests, telegram_id
            FROM bookings
            WHERE status = 'confirmed'
            AND date = ?
            """,
            (tomorrow,),
        )
        return cursor.fetchall()


# Функции для работы с меню
def add_menu_item(
    category: str, name: str, description: str, price: float, photo_url: str
) -> int:
    with get_db() as cursor:
        cursor.execute(
            """
                    INSERT INTO menu (category, name, description, price, photo_url)
                    VALUES (?, ?, ?, ?, ?)
                    """,
            (category, name, description, price, photo_url),
        )

        menu_id = cursor.lastrowid
        return menu_id


def get_menu() -> list:
    with get_db() as cursor:
        cursor.execute("""
                    SELECT id, category, name, description, price, photo_url
                    FROM menu
                    WHERE is_available = 1
                    ORDER BY category
        """)
        return cursor.fetchall()


def get_menu_by_category(category: str):
    with get_db() as cursor:
        cursor.execute(
            """
                    SELECT id, name, description, price, photo_url
                    FROM menu
                    WHERE is_available = 1 AND category = ?
                    ORDER BY name
                    """,
            (category,),
        )
        return cursor.fetchall()


def toggle_menu_item(item_id: int, is_available: int):
    with get_db() as cursor:
        cursor.execute(
            """
                UPDATE menu
                SET is_available = ?
                WHERE id = ?
            """,
            (is_available, item_id),
        )
