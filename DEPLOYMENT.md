# Deployment Guide - JC Icons Management System V2

This guide explains how to deploy the JC Icons Management System to production.

## Prerequisites

- Python 3.8+
- A production database (PostgreSQL recommended, or any SQLAlchemy-supported database)
- A production server (Heroku, AWS, DigitalOcean, etc.) or on-premises server
- A reverse proxy (Nginx, Apache) for on-premises deployments

## Quick Start - Local Development

1. **Clone the repository and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and set SECRET_KEY and other variables
   ```

3. **Generate a SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Run the development server:**
   ```bash
   python run.py
   ```

Visit `http://localhost:5000` and log in with username `admin` and password from `ADMIN_PASSWORD` in `.env`.

## Production Deployment

### Environment Variables (Required)

Create a `.env` file in production with these required variables:

```
# REQUIRED
SECRET_KEY=<generate-a-random-string>
FLASK_ENV=production
FLASK_DEBUG=false

# DATABASE (required for production)
DATABASE_URL=postgresql://user:password@host:5432/jc_icons_v2

# ADMIN USER (optional, only used if database is empty)
ADMIN_PASSWORD=<strong-password>
```

### Database Setup

For production, use PostgreSQL (or another external database):

```
# PostgreSQL URL format
DATABASE_URL=postgresql://username:password@hostname:5432/database_name

# MySQL URL format
DATABASE_URL=mysql://username:password@hostname:3306/database_name
```

The application will automatically create tables on first run.

### Option 1: Deploy to Heroku

1. **Install Heroku CLI and login:**
   ```bash
   heroku login
   ```

2. **Create a Heroku app:**
   ```bash
   heroku create your-app-name
   ```

3. **Add PostgreSQL add-on:**
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

4. **Set environment variables:**
   ```bash
   heroku config:set SECRET_KEY=<your-secret-key>
   heroku config:set FLASK_ENV=production
   heroku config:set ADMIN_PASSWORD=<strong-password>
   ```

5. **Deploy:**
   ```bash
   git push heroku main
   ```

6. **Run database migrations (if needed):**
   ```bash
   heroku run python
   ```

### Option 2: Deploy to AWS

1. **Create an EC2 instance** (Ubuntu 20.04 LTS recommended)

2. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-venv postgresql postgresql-contrib nginx
   ```

3. **Clone repository and set up virtual environment:**
   ```bash
   git clone <your-repo-url>
   cd jc-icons-management-system-v2
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   nano .env
   ```

5. **Create a systemd service file** at `/etc/systemd/system/jc-icons.service`:
   ```ini
   [Unit]
   Description=JC Icons Management System
   After=network.target
   
   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/jc-icons-management-system-v2
   Environment="PATH=/home/ubuntu/jc-icons-management-system-v2/venv/bin"
   ExecStart=/home/ubuntu/jc-icons-management-system-v2/venv/bin/gunicorn wsgi:app -b 127.0.0.1:5000
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

6. **Start the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start jc-icons
   sudo systemctl enable jc-icons
   ```

7. **Configure Nginx as reverse proxy:**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

8. **Enable HTTPS with Let's Encrypt:**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### Option 3: Deploy to DigitalOcean App Platform

1. **Push your code to GitHub**

2. **Create an app:**
   - Go to DigitalOcean Apps
   - Click "Create App"
   - Connect your GitHub repository
   - Select the repository and branch

3. **Configure the app:**
   - Set build command: `pip install -r requirements.txt`
   - Set run command: `gunicorn wsgi:app`

4. **Add PostgreSQL database:**
   - Add component → Database → PostgreSQL
   - Get the connection string and set it as `DATABASE_URL`

5. **Set environment variables:**
   - Go to Settings
   - Set `SECRET_KEY`, `FLASK_ENV=production`, and `ADMIN_PASSWORD`

6. **Deploy**

### Option 4: On-Premises Deployment

1. **Install Python and PostgreSQL:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-venv postgresql postgresql-contrib
   ```

2. **Set up application:**
   ```bash
   git clone <your-repo-url>
   cd jc-icons-management-system-v2
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create PostgreSQL database:**
   ```bash
   sudo -u postgres createuser jc_icons -P
   sudo -u postgres createdb jc_icons_v2 -O jc_icons
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Set DATABASE_URL to postgresql://jc_icons:password@localhost:5432/jc_icons_v2
   ```

5. **Use Gunicorn with a process manager (systemd, supervisor, etc.)**

## Production Best Practices

### Security

- ✅ Always use HTTPS in production
- ✅ Set `SECRET_KEY` to a random, secure value
- ✅ Use strong passwords for admin and database users
- ✅ Keep the `.env` file secure and never commit it
- ✅ Regularly update dependencies: `pip install --upgrade -r requirements.txt`
- ✅ Use a firewall to restrict access to your application
- ✅ Behind a reverse proxy (Nginx, Apache)

### Database

- ✅ Use an external database (PostgreSQL, MySQL, etc.) - NOT SQLite
- ✅ Enable automatic backups
- ✅ Use connection pooling for better performance
- ✅ Monitor database performance

### Monitoring & Logging

- ✅ Set up application logging
- ✅ Monitor error rates and performance
- ✅ Set up alerts for critical errors
- ✅ Keep application and system logs

### Backup & Disaster Recovery

- ✅ Regular database backups (daily minimum)
- ✅ Test backup restoration procedures
- ✅ Keep encrypted backup copies off-site

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U username -h hostname -d database_name
```

### Port Already in Use

```bash
# Change port in .env
FLASK_PORT=8000
```

### Permission Errors

```bash
# Ensure proper file permissions
chmod 755 -R /path/to/app
```

### Gunicorn Not Starting

```bash
# Test locally first
gunicorn wsgi:app --bind 0.0.0.0:5000
```

## Updating the Application

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Install new dependencies:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Restart the application:**
   ```bash
   # For systemd
   sudo systemctl restart jc-icons
   
   # For Heroku
   git push heroku main
   ```

## Getting Help

- Check application logs for error messages
- Review the [Flask documentation](https://flask.palletsprojects.com/)
- Review the [SQLAlchemy documentation](https://docs.sqlalchemy.org/)

---

**Last Updated:** February 2026  
**Deployment Checklist:** See DEPLOYMENT_CHECKLIST.md
