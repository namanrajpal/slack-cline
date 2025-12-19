"""
Database migration: Add title column to conversations table

This migration adds a title column to store conversation titles
derived from the first user message.

To run: python backend/migrations/add_conversation_title.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database import get_session, engine
from utils.logging import get_logger

logger = get_logger("migration")


async def migrate():
    """Add title column to conversations table."""
    
    logger.info("Starting migration: add title column to conversations")
    
    try:
        async with engine.begin() as conn:
            # Check if column already exists
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='conversations' AND column_name='title'
            """))
            
            if result.fetchone():
                logger.info("Column 'title' already exists, skipping migration")
                return
            
            # Add the title column
            await conn.execute(text("""
                ALTER TABLE conversations 
                ADD COLUMN title VARCHAR(255)
            """))
            
            logger.info("Successfully added 'title' column to conversations table")
            
            # Optionally, backfill titles from existing conversations
            result = await conn.execute(text("""
                SELECT id, state_json 
                FROM conversations 
                WHERE title IS NULL
            """))
            
            rows = result.fetchall()
            logger.info(f"Found {len(rows)} conversations without titles, backfilling...")
            
            for row in rows:
                conv_id = row[0]
                state_json = row[1]
                
                # Extract first user message
                title = "New conversation"
                if state_json and 'messages' in state_json:
                    for msg in state_json['messages']:
                        if msg.get('type') == 'HumanMessage':
                            content = msg.get('content', '')
                            if content:
                                title = content[:60] + ('...' if len(content) > 60 else '')
                                break
                
                # Update the conversation
                await conn.execute(
                    text("UPDATE conversations SET title = :title WHERE id = :id"),
                    {"title": title, "id": conv_id}
                )
            
            logger.info(f"Backfilled {len(rows)} conversation titles")
            
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(migrate())
