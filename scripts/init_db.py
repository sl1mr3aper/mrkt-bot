"""Initialise the SQLite database with all tables."""

from __future__ import annotations

import asyncio

from config import settings
from db.database import init_db


async def main() -> None:
    settings.ensure_dirs()
    db = init_db(settings.database_url)
    await db.create_all()
    print(f"Database ready at {settings.DATABASE_PATH}")
    await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
