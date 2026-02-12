# ⚡ Quick Start - Production Deployment

Get your JC Icons application running in production in 5 minutes.

## 1️⃣ Prepare Environment

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Copy environment template
cp .env.example .env

# Edit .env - replace these:
# SECRET_KEY=<your-generated-key>
# FLASK_ENV=production
# FLASK_DEBUG=false
nano .env
```

## 2️⃣ Choose Your Platform

### 🟣 Heroku (Easiest)

```bash
# Login
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Set variables
heroku config:set SECRET_KEY=<your-secret-key>
heroku config:set FLASK_ENV=production
heroku config:set ADMIN_PASSWORD=<strong-password>

# Deploy
git push heroku main

# Initialize database
heroku run python scripts/init_db.py init
```

Done! Your app is live at `https://your-app-name.herokuapp.com`

### 🐳 Docker (Local/Cloud)

```bash
# Start
docker-compose -f docker-compose-prod.yml --env-file .env.prod up -d

# Initialize
docker-compose -f docker-compose-prod.yml exec app python scripts/init_db.py init

# Check health
curl http://localhost:5000/health
```

### ☁️ AWS EC2

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Clone repository
git clone <your-repo>
cd jc-icons-management-system-v2

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env with your values
nano .env

# Initialize database
python scripts/init_db.py init

# Run server (in background)
nohup gunicorn -b 0.0.0.0:5000 wsgi:app > app.log 2>&1 &

# Check if running
curl http://localhost:5000/health
```

## 3️⃣ Access Your Application

| Platform | URL |
|----------|-----|
| Heroku | `https://your-app-name.herokuapp.com` |
| Docker | `http://localhost:5000` |
| AWS | `http://your-instance-ip:5000` |

**Login:**
- Username: `admin`
- Password: (from ADMIN_PASSWORD in .env)

## 4️⃣ Verify It's Working

```bash
# Health check
curl https://your-app-domain/health

# Expected response
{"status": "healthy", "message": "Application is running"}
```

## 5️⃣ Configure HTTPS (Important!)

### Heroku
✅ HTTPS automatically enabled

### Docker on Linux
```bash
sudo apt-get install certbot nginx
sudo certbot certonly --standalone -d your-domain.com
# Configure Nginx to reverse proxy port 5000
```

### AWS EC2
```bash
# Install Nginx
sudo apt-get install nginx certbot python3-certbot-nginx

# Get free SSL
sudo certbot --nginx -d your-domain.com
```

## 📋 Essential Commands

```bash
# Create a user
docker-compose exec app python scripts/init_db.py create-user

# Check logs
docker-compose logs app

# Reset database (dev only)
docker-compose exec app python scripts/init_db.py reset

# Backup database
docker-compose exec postgres pg_dump -U jc_icons jc_icons_v2 > backup.sql
```

## ❌ Troubleshooting

**App won't start:**
```bash
# Check SECRET_KEY is set
echo $SECRET_KEY

# Check logs
docker-compose logs app
```

**Database error:**
```bash
# Test database connection
docker-compose exec app python -c "from app import create_app; app = create_app(); print('✓ DB works')"
```

**Port already in use:**
```bash
# Change port in docker-compose.yml
# ports:
#   - "8000:5000"
```

## 📚 More Help

- Full guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Docker guide: [DEPLOYMENT_DOCKER.md](DEPLOYMENT_DOCKER.md)
- Checklist: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- Full details: [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md)

---

**That's it!** Your application should now be running in production. 🎉
