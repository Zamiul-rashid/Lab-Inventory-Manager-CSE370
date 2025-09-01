# deployment_guide.py - Django Deployment Best Practices

# 1. Production Settings (settings_production.py)
"""
Create separate settings for production environment
"""

from .settings import *
import os

# Security Settings
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com', '127.0.0.1']

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Database Configuration for Production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Static Files Configuration
STATIC_ROOT = '/var/www/yourdomain/static/'
MEDIA_ROOT = '/var/www/yourdomain/media/'

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'Lab Inventory Manager <noreply@yourdomain.com>'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/lit_app.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/lit_errors.log',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Security Key from Environment
SECRET_KEY = os.environ.get('SECRET_KEY')

# Admin Notifications
ADMINS = [
    ('Admin Name', 'admin@yourdomain.com'),
]

MANAGERS = ADMINS

# 2. Environment Variables (.env file)
"""
Create .env file for sensitive configuration:

SECRET_KEY=your-very-secret-key-here
DB_NAME=lit_production
DB_USER=lit_user
DB_PASSWORD=secure_password_123
DB_HOST=localhost
DB_PORT=5432
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
"""

# 3. Requirements Files

# requirements/base.txt
"""
Django==4.2.23
mysqlclient==2.1.1
pillow==9.5.0
django-crispy-forms==2.0
crispy-bootstrap4==2022.1
python-decouple==3.8
"""

# requirements/production.txt
"""
-r base.txt
gunicorn==20.1.0
psycopg2-binary==2.9.7
redis==4.6.0
django-redis==5.3.0
whitenoise==6.5.0
sentry-sdk==1.32.0
"""

# 4. Docker Configuration

# Dockerfile
"""
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        postgresql-client \\
        build-essential \\
        libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput --settings=lit_project.settings_production

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "lit_project.wsgi:application"]
"""

# docker-compose.yml
"""
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
    depends_on:
      - db
      - redis

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/var/www/static
      - media_volume:/var/www/media
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
"""

# 5. Nginx Configuration

# nginx.conf
"""
events {
    worker_connections 1024;
}

http {
    upstream django {
        server web:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        client_max_body_size 20M;

        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        location /media/ {
            alias /var/www/media/;
            expires 1y;
            add_header Cache-Control "public";
        }

        location / {
            proxy_pass http://django;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
        }
    }
}
"""

# 6. Systemd Service (for VPS deployment)

# /etc/systemd/system/lit-app.service
"""
[Unit]
Description=Lab Inventory Tracker
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/lit-app
Environment="DJANGO_SETTINGS_MODULE=lit_project.settings_production"
EnvironmentFile=/var/www/lit-app/.env
ExecStart=/var/www/lit-app/venv/bin/gunicorn --workers 3 --bind unix:/var/www/lit-app/lit-app.sock lit_project.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
"""

# 7. Deployment Script

# deploy.sh
"""
#!/bin/bash

# Lab Inventory Tracker Deployment Script

set -e

echo "Starting deployment..."

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements/production.txt

# Run migrations
python manage.py migrate --settings=lit_project.settings_production

# Collect static files
python manage.py collectstatic --noinput --settings=lit_project.settings_production

# Restart services
sudo systemctl restart lit-app
sudo systemctl restart nginx

echo "Deployment completed successfully!"
"""

# 8. Health Check Endpoint

# Add to views.py
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    '''Health check endpoint for monitoring'''
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check cache connection
    try:
        cache.set('health_check', 'ok', 10)
        cache_status = "healthy" if cache.get('health_check') == 'ok' else "error"
    except Exception as e:
        cache_status = f"error: {str(e)}"
    
    status = {
        'status': 'healthy' if db_status == 'healthy' and cache_status == 'healthy' else 'unhealthy',
        'database': db_status,
        'cache': cache_status,
        'version': '1.0.0'
    }
    
    return JsonResponse(status)
"""

# 9. Monitoring with Sentry

# Add to settings_production.py
"""
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn-here",
    integrations=[
        DjangoIntegration(
            transaction_style='url',
        ),
    ],
    traces_sample_rate=0.1,
    send_default_pii=True
)
"""

# 10. Backup Script

# backup.sh
"""
#!/bin/bash

# Database backup
BACKUP_DIR="/var/backups/lit-app"
DATE=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -h localhost -U lit_user lit_production > "$BACKUP_DIR/database_$DATE.sql"

# Media files backup
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" /var/www/lit-app/media/

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
"""

# 11. SSL Certificate with Let's Encrypt

# ssl_setup.sh
"""
#!/bin/bash

# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal cron job
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
"""

# 12. Performance Monitoring

# Add to settings_production.py
"""
# Enable database query logging in production (temporarily for debugging)
LOGGING['loggers']['django.db.backends'] = {
    'level': 'DEBUG',
    'handlers': ['file'],
    'propagate': False,
}

# Monitor slow queries
DATABASES['default']['OPTIONS']['options'] = '-c log_min_duration_statement=1000'
"""

# Deployment Checklist:
"""
□ Set DEBUG = False
□ Configure ALLOWED_HOSTS
□ Set up proper database (PostgreSQL recommended)
□ Configure static file serving
□ Set up SSL/HTTPS
□ Configure email backend
□ Set up logging
□ Create superuser account
□ Run collectstatic
□ Run migrations
□ Set up backup system
□ Configure monitoring
□ Test all functionality
□ Set up health checks
□ Configure auto-deployment (CI/CD)
"""
