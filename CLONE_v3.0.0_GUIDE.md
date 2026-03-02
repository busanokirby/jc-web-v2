# How to Clone JC-Web v3.0.0

This guide provides instructions for cloning the stable v3.0.0 release of the JC Icons Computer Sales & Services application.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Git** - Version control system ([Download](https://git-scm.com/download/win))
- **Python 3.8+** - Programming language ([Download](https://www.python.org/downloads/))
- **pip** - Python package manager (usually comes with Python)

## Clone the Repository

### Option 1: Clone Latest Main Branch (Recommended for Development)

```bash
git clone https://github.com/busanokirby/jc-web-v2.git
cd jc-web-v2
```

### Option 2: Clone Specific v3.0.0 Tag (Recommended for Production)

```bash
git clone --branch v3.0.0 --depth 1 https://github.com/busanokirby/jc-web-v2.git
cd jc-web-v2
```

### Option 3: Clone and Checkout v3.0.0 Tag

```bash
git clone https://github.com/busanokirby/jc-web-v2.git
cd jc-web-v2
git checkout v3.0.0
```

## Setup Instructions

### 1. Create Python Virtual Environment

**Windows:**
```bash
python -m venv webv2
.\webv2\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv webv2
source webv2/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example config (if available) or create manually
cp .env.example .env
```

Edit `.env` with your configuration:

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/jc_icons_v2.db
FLASK_ENV=production
FLASK_DEBUG=False

# SMTP Configuration
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=True
SENDER_NAME=JC ICONS DAILY SALES REPORT

# Application Settings
JOBS_STORE=memory
```

### 4. Initialize Database

```bash
# Create instance directory if it doesn't exist
mkdir instance

# Apply database migrations
flask db upgrade
```

### 5. Run the Application

**Development Server:**
```bash
flask run
```

**Production Server (Waitress):**
```bash
waitress-serve --host 0.0.0.0 --port 5000 wsgi:app
```

Access the application at: `http://localhost:5000`

## Verify Installation

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check Git tags
git tag -l

# Verify current version
git describe --tags
```

## What's New in v3.0.0

✅ **Service Layer Refactoring**
- Fixed timezone bugs (all operations now Philippines UTC+8)
- Removed silent failures in email service
- Centralized calculations in ReportService

✅ **Database Improvements**
- Added Flask-Migrate for database versioning
- Alembic infrastructure configured
- Notes column added to sale table

✅ **UI Enhancements**
- Interactive customer search in add repairs form
- Custom device type support
- Invoice improvements (notes hidden from print)

✅ **Email Service**
- No file attachments in automated emails
- Frequency checking prevents duplicate sends
- Clean logging (debug statements removed)

✅ **Type Safety**
- Pylance type hint errors fixed
- Proper import patterns with TYPE_CHECKING

## Troubleshooting

### Python Version Issues
```bash
# Use specific Python version
python3.10 -m venv webv2
```

### Database Migration Errors
```bash
# Reset migrations (caution - loses data)
flask db stamp head
flask db upgrade
```

### Virtual Environment Not Activating (Windows)
```bash
# If PowerShell execution policy blocks activation
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try again
.\webv2\Scripts\Activate.ps1
```

### SMTP Connection Issues
- Verify SMTP server address and port
- Check username and password
- Ensure firewall allows outbound connections
- For Gmail, enable "Less secure app access" or use App Password

## Additional Resources

- **GitHub Repository**: https://github.com/busanokirby/jc-web-v2
- **Release Tags**: `git tag -l`
- **Documentation**: Check `README.md` in project root

## Support

For issues or questions:
1. Check existing GitHub issues
2. Review logs in `instance/` directory
3. Run `flask db current` to check migration status

---

**Version**: 3.0.0  
**Release Date**: March 2, 2026  
**Status**: Stable
