#!/usr/bin/env python
"""
Database initialization and migration script

Usage:
    python scripts/init_db.py init      # Initialize database with tables
    python scripts/init_db.py reset     # Reset database (development only)
    python scripts/init_db.py create-user  # Create a new user
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def init_database():
    """Initialize database with tables"""
    from app import create_app
    from app.extensions import db
    
    app = create_app()
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully")


def reset_database():
    """Reset database (development only)"""
    from app import create_app
    from app.extensions import db
    
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        print("❌ Cannot reset database in production!")
        sys.exit(1)
    
    confirm = input("⚠️  This will delete all data. Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        print("Reset cancelled")
        return
    
    app = create_app()
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("✓ All tables dropped")
        
        print("Creating new tables...")
        db.create_all()
        print("✓ Database reset successfully")


def create_user():
    """Create a new user"""
    from app import create_app
    from app.models.user import User
    from app.extensions import db
    from werkzeug.security import generate_password_hash
    
    app = create_app()
    with app.app_context():
        username = input("Username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return
        
        if User.query.filter_by(username=username).first():
            print(f"❌ User '{username}' already exists")
            return
        
        full_name = input("Full Name: ").strip()
        password = input("Password: ").strip()
        
        if not password:
            print("❌ Password cannot be empty")
            return
        
        print("\nAvailable roles:")
        print("  1. ADMIN - Full system access")
        print("  2. SALES - Sales and customer access")
        print("  3. TECH - Repair and technician access")
        
        role_choice = input("Select role (1-3) [default: 2]: ").strip()
        role_map = {'1': 'ADMIN', '2': 'SALES', '3': 'TECH'}
        role = role_map.get(role_choice, 'SALES')
        
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            full_name=full_name or username,
            role=role
        )
        db.session.add(user)
        db.session.commit()
        
        print(f"✓ User '{username}' created successfully with role '{role}'")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'init':
        init_database()
    elif command == 'reset':
        reset_database()
    elif command == 'create-user':
        create_user()
    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
