"""
Script to initialize database tables for LinguaMate AI.
"""

import asyncio
from app.database import engine, Base
from app.models import *  # Imports all SQLAlchemy models


async def init_tables():
    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_tables())
