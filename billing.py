"""Billing and payments management for the Telegram bot."""

import aiosqlite
from datetime import datetime, timezone

DATABASE = "transcriptions.db"


async def init_billing_table():
    """Create billing table and index if they don't exist."""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS billing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hashed_user_id TEXT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                source TEXT NOT NULL,
                telegram_payment_id TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_billing_hashed_user_id 
            ON billing(hashed_user_id)
        """)
        await db.commit()


async def add_billing_record(
    hashed_user_id: str,
    amount: float,
    source: str,
    telegram_payment_id: str | None = None,
) -> int:
    """
    Add a billing record.

    Args:
        hashed_user_id: SHA256 hash of the Telegram user ID
        amount: Transaction amount (positive for credits, negative for charges)
        source: Transaction type (e.g., 'telegram_payment', 'usage_charge', 'admin_adjustment')
        telegram_payment_id: Optional Telegram payment reference ID

    Returns:
        The ID of the created billing record
    """
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """
            INSERT INTO billing (hashed_user_id, amount, source, telegram_payment_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                hashed_user_id,
                amount,
                source,
                telegram_payment_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_balance(hashed_user_id: str) -> float:
    """
    Get total balance for a user (sum of all amounts).

    Args:
        hashed_user_id: SHA256 hash of the Telegram user ID

    Returns:
        The user's current balance
    """
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM billing WHERE hashed_user_id = ?",
            (hashed_user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return float(row[0])


async def decrement_balance(
    hashed_user_id: str,
    amount: float,
    source: str,
) -> int:
    """
    Decrement user balance (convenience wrapper for charges).

    Args:
        hashed_user_id: SHA256 hash of the Telegram user ID
        amount: Amount to subtract (must be positive, will be stored as negative)
        source: Transaction type (e.g., 'usage_charge')

    Returns:
        The ID of the created billing record
    """
    return await add_billing_record(
        hashed_user_id=hashed_user_id,
        amount=-abs(amount),
        source=source,
    )
