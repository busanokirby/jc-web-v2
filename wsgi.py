"""
WSGI entry point for production servers (Gunicorn, uWSGI, etc.)
Use this file to run the app in production environments

Example:
    gunicorn wsgi:app
"""
import os
import sys
from pathlib import Path

# Load environment variables
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

# Ensure SECRET_KEY is set
if not os.environ.get('SECRET_KEY'):
    print("ERROR: SECRET_KEY environment variable must be set!", file=sys.stderr)
    sys.exit(1)

from app import create_app
from config import get_config

# Get the appropriate configuration
config_class = get_config()

# Create the app
app = create_app(config_class)

if __name__ == "__main__":
    app.run()
