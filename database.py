import sqlite3

DB_NAME = "cafe.db"

def init_db():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

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
    conn.commit()
    conn.close()

def save_booking(name: str, phone: str, date: str, guests: int) -> int:

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
                   INSERT INTO bookings (name, phone, date, guests)
                   VALUES (?, ?, ?, ?)
                   """, (name, phone, date, guests))

    booking_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return booking_id

def get_all_bookings() -> list:

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT id, name, phone, date, guests, created_at
                   FROM bookings
                   ORDER BY created_at DESC
                   """)

    rows = cursor.fetchall()
    conn.close()
    return rows

def get_stats() -> dict:

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM bookings")
    total = cursor.fetchone()[0]

    cursor.execute("""
                   SELECT COUNT(*) FROM bookings
                   WHERE DATE(created_at) = Date('now')
                   """)
    today = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(guests) FROM bookings")
    total_guests = cursor.fetchone()[0] or 0

    conn.close()

    return {
        "total": total,
        "today": today,
        "total_guests": total_guests
    }
