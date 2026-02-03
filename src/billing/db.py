import hashlib
import os
from datetime import UTC, datetime

import aiosqlite

DATABASE_PATH = os.getenv("DATABASE_PATH", "./billing.db")


def hash_user_id(user_id: int) -> str:
    """Hash user ID using SHA-256 for privacy."""
    return hashlib.sha256(str(user_id).encode()).hexdigest()


async def init_billing_db() -> None:
    """Create billing table if it doesn't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS billing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_hash TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)
        await db.commit()


async def bill(user_hash: str, amount: float, source: str) -> None:
    """Record a billing entry.

    Args:
        user_hash: SHA-256 hash of Telegram user ID
        amount: Positive for topups, negative for consumption (in seconds)
        source: 'telegram_payment', 'transcribing', etc.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO billing (user_hash, amount, date, source) VALUES (?, ?, ?, ?)",
            (user_hash, amount, datetime.now(UTC).isoformat(), source),
        )
        await db.commit()


async def get_balance(user_hash: str) -> float:
    """Get user's current balance (sum of all transactions).

    Args:
        user_hash: SHA-256 hash of Telegram user ID

    Returns:
        Current balance in seconds (can be negative if user overspent)
    """
    async with (
        aiosqlite.connect(DATABASE_PATH) as db,
        db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM billing WHERE user_hash = ?",
            (user_hash,),
        ) as cursor,
    ):
        row = await cursor.fetchone()
        return row[0] if row else 0.0
