import aiosqlite
import datetime

db_path = "transcriptions.db"

async def get_used_month_seconds(hashed_user_id: int) -> int:
    last_month = datetime.datetime.now() - datetime.timedelta(days=30)
    last_month_str = last_month.strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT SUM(audio_duration) FROM transcriptions WHERE hashed_user_id = ? AND created_at >= ?", (hashed_user_id, last_month_str))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def insert_transcription_log(hashed_user_id: str, audio_duration: int, transcription_time: int, created_at: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("INSERT INTO transcriptions (hashed_user_id, audio_duration, transcription_time, created_at) VALUES (?, ?, ?, ?)", (hashed_user_id, audio_duration, transcription_time, created_at))
        await db.commit()


async def generate_db():
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS transcriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        hashed_user_id TEXT,
                        audio_duration INTEGER,
                        transcription_time REAL,
                        created_at TEXT
                    )""")
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_requests_on_time
            ON transcriptions (hashed_user_id, created_at);
            """)
        await db.commit()
    print("DB generated")
