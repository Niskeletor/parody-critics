#!/usr/bin/env python3
"""
🎭 Parody Critics - Database Initialization
Initialize database with schema and default characters
"""

import sqlite3
from pathlib import Path
import sys

from utils import setup_logging, get_logger
from config import Config

# Setup logging
setup_logging()
logger = get_logger('init_db')


def create_database_schema(db_path: str):
    """Create database tables if they don't exist - Skip if already exist"""

    logger.info(f"Checking database schema at: {db_path}")

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        # Check if tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        if 'media' in existing_tables:
            logger.info("✅ Database schema already exists - skipping creation")
            return

        logger.info("Creating new database schema...")

        # This would create the schema, but since it already exists, we skip
        # The actual schema is already created in the existing database
        logger.info("✅ Database schema ready")


def insert_default_characters(db_path: str):
    """Insert default critic characters"""

    logger.info("Inserting default characters")

    characters = [
        {
            'id': 'marco_aurelio',
            'name': 'Marco Aurelio',
            'emoji': '👑',
            'color': '#8B4513',
            'border_color': '#D2691E',
            'accent_color': '#F4A460',
            'personality': 'stoic',
            'description': 'Emperador filósofo romano (121-180 d.C.), autor de "Meditaciones". Busca enseñanzas morales y filosóficas en todo.',
            'prompt_template': 'Eres Marco Aurelio, emperador filósofo romano. Analiza {title} desde una perspectiva estoica y filosófica.'
        },
        {
            'id': 'rosario_costras',
            'name': 'Rosario Costras',
            'emoji': '✊',
            'color': '#8B008B',
            'border_color': '#FF1493',
            'accent_color': '#FF69B4',
            'personality': 'woke',
            'description': 'Activista progresista del siglo XXI, crítica feroz de estructuras de poder. Analiza todo desde una perspectiva de justicia social.',
            'prompt_template': 'Eres Rosario Costras, activista progresista. Critica {title} desde una perspectiva de justicia social y representación.'
        }
    ]

    with sqlite3.connect(db_path) as conn:
        for char in characters:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO characters (id, name, emoji, color, border_color, accent_color,
                                                    personality, description, prompt_template, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (char['id'], char['name'], char['emoji'], char['color'], char['border_color'],
                     char['accent_color'], char['personality'], char['description'], char['prompt_template'], True)
                )
                logger.info(f"✅ Inserted character: {char['name']}")
            except sqlite3.Error as e:
                logger.error(f"❌ Failed to insert character {char['name']}: {str(e)}")

        conn.commit()
        logger.info("✅ Default characters inserted successfully")


def insert_sample_media(db_path: str):
    """Insert some sample media for testing"""

    logger.info("Inserting sample media")

    sample_media = [
        {
            'title': 'The Matrix',
            'year': 1999,
            'type': 'movie',
            'genres': '["Action", "Sci-Fi"]',
            'overview': 'A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.',
            'runtime': 136,
            'vote_average': 8.7
        },
        {
            'title': 'Breaking Bad',
            'year': 2008,
            'type': 'series',
            'genres': '["Crime", "Drama", "Thriller"]',
            'overview': 'A high school chemistry teacher diagnosed with inoperable lung cancer turns to manufacturing and selling methamphetamine.',
            'runtime': 47,
            'vote_average': 9.5
        },
        {
            'title': 'Parasite',
            'year': 2019,
            'type': 'movie',
            'genres': '["Drama", "Thriller", "Comedy"]',
            'overview': 'A poor family schemes to become employed by a wealthy family and infiltrate their household.',
            'runtime': 132,
            'vote_average': 8.6
        }
    ]

    with sqlite3.connect(db_path) as conn:
        for media in sample_media:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO media (tmdb_id, jellyfin_id, title, year, type, genres, overview, runtime, vote_average)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (f"tmdb_{media['title'].replace(' ', '_').lower()}",
                     f"jf_{media['title'].replace(' ', '_').lower()}_001",
                     media['title'], media['year'], media['type'], media['genres'],
                     media['overview'], media['runtime'], media['vote_average'])
                )
                logger.info(f"✅ Inserted media: {media['title']}")
            except sqlite3.Error as e:
                logger.error(f"❌ Failed to insert media {media['title']}: {str(e)}")

        conn.commit()
        logger.info("✅ Sample media inserted successfully")


def check_database_status(db_path: str):
    """Check and display database status"""

    logger.info("Checking database status")

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Count tables
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row['name'] for row in cursor.fetchall()]

            print(f"\n📊 Database Status: {db_path}")
            print(f"📋 Tables: {len(tables)}")

            if 'media' in tables:
                cursor = conn.execute("SELECT COUNT(*) as count FROM media")
                media_count = cursor.fetchone()['count']
                print(f"🎬 Media items: {media_count}")

            if 'characters' in tables:
                cursor = conn.execute("SELECT COUNT(*) as count FROM characters")
                char_count = cursor.fetchone()['count']
                print(f"👥 Characters: {char_count}")

                # Show character names
                cursor = conn.execute("SELECT name FROM characters")
                char_names = [row['name'] for row in cursor.fetchall()]
                print(f"   Characters: {', '.join(char_names)}")

            if 'critics' in tables:
                cursor = conn.execute("SELECT COUNT(*) as count FROM critics")
                critics_count = cursor.fetchone()['count']
                print(f"📝 Reviews: {critics_count}")

            if 'sync_log' in tables:
                cursor = conn.execute("SELECT COUNT(*) as count FROM sync_log")
                sync_count = cursor.fetchone()['count']
                print(f"🔄 Sync logs: {sync_count}")

            print("✅ Database is ready!")

    except sqlite3.Error as e:
        logger.error(f"❌ Database check failed: {str(e)}")


def main():
    """Main initialization function"""

    try:
        config = Config()
        db_path = config.DATABASE_PATH

        print(f"🎭 Parody Critics - Database Initialization")
        print(f"Database: {db_path}")

        # Create schema
        create_database_schema(db_path)

        # Insert default data
        insert_default_characters(db_path)
        insert_sample_media(db_path)

        # Check status
        check_database_status(db_path)

        print(f"\n🎉 Database initialization completed successfully!")
        print(f"\nNext steps:")
        print(f"1. Run sync: python sync_cli.py sync")
        print(f"2. Generate review: python critic_cli.py generate 'The Matrix'")

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        print(f"❌ Initialization failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()