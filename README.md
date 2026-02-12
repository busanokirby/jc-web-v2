# JC Icons Management System V2

A comprehensive Flask-based inventory, repair, and sales management system for JC Icons.

## Features

- **Inventory Management** - Track products, stock levels, and inventory movements
- **Repair Tracking** - Manage repair tickets and technician assignments
- **Customer Management** - Maintain customer information and repair history
- **Sales & POS** - Process sales transactions and generate invoices
- **Reports** - Financial and inventory reporting
- **User Management** - Role-based access control (ADMIN, SALES, TECH)
- **Feature Toggles** - Configure features via admin panel (POS, SALES inventory edit, TECH details view)

## Technology Stack

- **Backend:** Python 3.8+, Flask 3.0
- **Database:** SQLite (development) / PostgreSQL (production)
- **Frontend:** HTML5, Bootstrap 5, JavaScript
- **Authentication:** Flask-Login with password hashing

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd jc-icons-management-system-v2
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```

5. **Generate a SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output and add it to your `.env` file:
   ```
   SECRET_KEY=<paste-generated-key>
   ```

6. **Run the development server:**
   ```bash
   python run.py
   ```

7. **Access the application:**
   - Open http://localhost:5000 in your browser
   - Login with username `admin` and password specified in `.env` (default: `admin123`)

## Directory Structure

```
jc-icons-management-system-v2/
├── app/                          # Flask application
│   ├── blueprints/              # Route modules
│   │   ├── auth/                # Authentication
│   │   ├── core/                # Dashboard & settings
│   │   ├── inventory/           # Inventory management
│   │   ├── repairs/             # Repair tracking
│   │   ├── sales/               # Sales & POS
│   │   ├── customers/           # Customer management
│   │   ├── users/               # User management
│   │   └── reports/             # Reporting
│   ├── models/                  # Database models
│   ├── services/                # Business logic
│   ├── static/                  # CSS, JavaScript, images
│   └── templates/               # HTML templates
├── tests/                        # Unit and integration tests
├── instance/                     # Instance-specific files (SQLite DB)
├── run.py                        # Development server entry point
├── wsgi.py                       # Production server entry point
├── config.py                     # Configuration management
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── Procfile                      # Heroku deployment config
└── DEPLOYMENT.md                 # Deployment guide
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `SECRET_KEY` - Flask session encryption key (required)
- `FLASK_ENV` - Environment: `development`, `testing`, or `production`
- `FLASK_DEBUG` - Enable debug mode: `true` or `false`
- `ADMIN_PASSWORD` - Initial admin password (used on first setup)
- `DATABASE_URL` - Database connection URL (production only)

## Development

### Running Tests

```bash
pytest
```

### Running with Debug Mode

```bash
export FLASK_DEBUG=true
python run.py
```

### Database Reset

To reset the database (development only):

1. Delete the `instance/jc_icons_v2.db` file
2. Restart the application - a new database will be created automatically

## User Roles

- **ADMIN** - Full system access, including settings
- **SALES** - Access to customers, sales, and POS
- **TECH** - Access to repairs and technician functions (based on feature toggle)

## Feature Toggles

Managed in **Admin → Settings → Feature Toggles:**

- **POS Enabled** - Enable/disable Point of Sale module
- **SALES Can Edit Inventory** - Allow SALES role to add/edit inventory
- **TECH Can View Details** - Allow TECH role to view repair/customer details

## Deployment

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on:

- Heroku deployment
- AWS EC2 deployment
- On-premises deployment
- Environment configuration
- Database setup
- Security best practices

Use the [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) before going live.

## Common Tasks

### Add a New User

```bash
python
from app import create_app
from app.models.user import User
from app.extensions import db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = User(
        username='john',
        password_hash=generate_password_hash('password123'),
        full_name='John Doe',
        role='SALES'  # or 'TECH'
    )
    db.session.add(user)
    db.session.commit()
    print("User created successfully")
```

### Reset Admin Password

```bash
python
from app import create_app
from app.models.user import User
from app.extensions import db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
        admin.password_hash = generate_password_hash('newpassword')
        db.session.commit()
        print("Admin password reset")
```

### View All Routes

```bash
python scripts/list_routes.py
```

## Troubleshooting

### Port Already in Use

```bash
export FLASK_PORT=8000
python run.py
```

### Database Locked

Ensure no other instances are running:

```bash
# Find and kill the process
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:5000 | xargs kill -9
```

### Import Errors

Make sure virtual environment is activated:

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests to ensure nothing is broken
4. Commit with clear messages
5. Submit a pull request

## Security

- Always use HTTPS in production
- Keep `SECRET_KEY` private and change it in production
- Use strong passwords
- Regularly update dependencies
- Review the [DEPLOYMENT.md](DEPLOYMENT.md) security section

## Getting Help

- Check the [DEPLOYMENT.md](DEPLOYMENT.md) for deployment questions
- Review Flask documentation: https://flask.palletsprojects.com/
- Check SQLAlchemy docs: https://docs.sqlalchemy.org/

## License

Proprietary - JC Icons Management System

## Support

For support, contact your system administrator or development team.

---

**Last Updated:** February 2026  
**Version:** 2.0.0
