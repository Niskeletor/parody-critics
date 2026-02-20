#!/usr/bin/env python3
"""
Complete setup and test script for Parody Critics API
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description, check=True):
    """Run shell command with logging"""
    print(f"🔧 {description}")
    print(f"   Command: {cmd}")

    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   ❌ stderr: {e.stderr}")
        return False

def setup_environment():
    """Setup Python environment and dependencies"""
    print("🐍 Setting up Python environment...")

    # Check Python version
    print(f"Python version: {sys.version}")

    # Install requirements if needed
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print("📦 Installing dependencies...")
        run_command("pip install -r requirements.txt", "Installing requirements")
    else:
        print("⚠️ requirements.txt not found")

def initialize_database():
    """Initialize SQLite database"""
    print("\n🗃️ Initializing database...")

    # Change to project directory
    os.chdir(Path(__file__).parent)

    # Run database initialization
    run_command("python database/init_db.py", "Creating database schema")

def test_database():
    """Test database functionality"""
    print("\n🧪 Testing database...")

    import sqlite3

    db_path = "database/critics.db"
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Test basic queries
            cursor.execute("SELECT COUNT(*) FROM characters WHERE active = TRUE")
            active_chars = cursor.fetchone()[0]
            print(f"   ✅ Active characters: {active_chars}")

            cursor.execute("SELECT COUNT(*) FROM media")
            total_media = cursor.fetchone()[0]
            print(f"   ✅ Total media: {total_media}")

            cursor.execute("SELECT COUNT(*) FROM critics")
            total_critics = cursor.fetchone()[0]
            print(f"   ✅ Total critics: {total_critics}")

            return True

    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        return False

def insert_test_data():
    """Insert some test data"""
    print("\n🎬 Inserting test data...")

    import sqlite3

    test_data = {
        "tmdb_id": "338969",
        "jellyfin_id": "629a781f6b78a86dd28b952783edeafe",
        "title": "El Vengador Tóxico",
        "year": 2025,
        "type": "movie",
        "overview": "Cuando un conserje oprimido sufre un accidente tóxico, se transforma en un héroe."
    }

    try:
        with sqlite3.connect("database/critics.db") as conn:
            cursor = conn.cursor()

            # Insert test media
            cursor.execute("""
                INSERT OR REPLACE INTO media
                (tmdb_id, jellyfin_id, title, year, type, overview)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                test_data["tmdb_id"],
                test_data["jellyfin_id"],
                test_data["title"],
                test_data["year"],
                test_data["type"],
                test_data["overview"]
            ))

            media_id = cursor.lastrowid or cursor.execute(
                "SELECT id FROM media WHERE tmdb_id = ?", (test_data["tmdb_id"],)
            ).fetchone()[0]

            # Insert test critics
            test_critics = [
                {
                    "character_id": "marco_aurelio",
                    "rating": 8,
                    "content": "Como emperador y filósofo, he contemplado muchas transformaciones..."
                },
                {
                    "character_id": "rosario_costras",
                    "rating": 2,
                    "content": "Esta película perpetúa múltiples violencias sistémicas..."
                }
            ]

            for critic in test_critics:
                cursor.execute("""
                    INSERT OR REPLACE INTO critics
                    (media_id, character_id, rating, content)
                    VALUES (?, ?, ?, ?)
                """, (media_id, critic["character_id"], critic["rating"], critic["content"]))

            conn.commit()
            print(f"   ✅ Test data inserted for '{test_data['title']}'")
            return True

    except Exception as e:
        print(f"   ❌ Failed to insert test data: {e}")
        return False

def start_api_server():
    """Start the FastAPI server"""
    print("\n🚀 Starting FastAPI server...")
    print("   Server will be available at: http://localhost:8000")
    print("   API docs will be available at: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop the server")

    try:
        os.chdir("api")
        os.system("python main.py")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")

def main():
    """Main setup function"""
    print("🎭 Parody Critics API Setup")
    print("=" * 50)

    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    success = True

    # Setup steps
    setup_environment()

    if not initialize_database():
        success = False

    if not test_database():
        success = False

    if not insert_test_data():
        success = False

    if success:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Test the API: python run_setup.py --start-server")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Test endpoint: http://localhost:8000/api/critics/338969")

        # Ask if user wants to start server
        if len(sys.argv) > 1 and "--start-server" in sys.argv:
            start_api_server()
        else:
            start_server = input("\n🚀 Start API server now? (y/N): ").lower().strip()
            if start_server == 'y':
                start_api_server()

    else:
        print("\n❌ Setup failed! Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()