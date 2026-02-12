from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

# Where to send users when they hit a protected page
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"