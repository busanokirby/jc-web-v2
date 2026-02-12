"""
JC Icons Management System V2
Entry point for the Flask application - Development Only

For production, use wsgi.py with a production server like Gunicorn
"""
import os
import sys
from pathlib import Path

# Load environment variables from .env file
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

from app import create_app
from config import get_config

if __name__ == '__main__':
    # Ensure instance folder exists
    os.makedirs('instance', exist_ok=True)
    
    # Get the appropriate config
    config_class = get_config()
    
    # Create app with config
    app = create_app(config_class)
    
    # Get debug mode from environment, default to True for development
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() in ('true', '1', 'yes')
    
    # Get host and port
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"Starting JC Icons Management System - {config_class.__name__}")
    print(f"Debug mode: {debug}")
    print(f"Server: {host}:{port}")
    
    app.run(debug=debug, host=host, port=port)