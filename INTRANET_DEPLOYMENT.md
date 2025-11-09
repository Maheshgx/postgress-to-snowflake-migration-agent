# Company Intranet Deployment Guide

Complete guide for deploying the PostgreSQL to Snowflake Migration Agent on your company intranet for internal use.

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Options](#architecture-options)
4. [Security Considerations](#security-considerations)
5. [Step-by-Step Deployment](#step-by-step-deployment)
6. [Network Configuration](#network-configuration)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Deployment Overview

### What You'll Deploy

- **Backend API** - FastAPI application (port 8000)
- **Frontend Web UI** - React SPA served via Nginx (port 80/443)
- **PostgreSQL** - Optional test database (port 5432)
- **Reverse Proxy** - Nginx for SSL termination and routing
- **Load Balancer** - Optional for high availability

### Infrastructure Requirements

**Minimum (Single Server):**
- 4 CPU cores
- 8 GB RAM
- 100 GB disk space
- Ubuntu 20.04+ or RHEL 8+
- Docker & Docker Compose

**Recommended (Production):**
- 8 CPU cores
- 16 GB RAM
- 500 GB disk space (for artifacts)
- Load balancer (HAProxy/Nginx)
- Centralized logging (ELK/Splunk)
- Monitoring (Prometheus/Grafana)

---

## Prerequisites

### 1. Server Access

```bash
# You need:
- SSH access to intranet server
- Sudo/root privileges
- Ability to open firewall ports
- DNS entry or IP address for internal access
```

### 2. Required Software

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

### 3. Network Requirements

- **Outbound access** to Snowflake (*.snowflakecomputing.com:443)
- **Outbound access** to Okta (your-domain.okta.com:443)
- **Inbound access** from internal network (port 80/443)
- **Database access** to PostgreSQL sources

### 4. SSL Certificate

```bash
# Option 1: Internal CA signed certificate
# Get from your IT/Security team

# Option 2: Self-signed (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/migration-agent.key \
  -out /etc/ssl/certs/migration-agent.crt \
  -subj "/CN=migration-agent.company.local"
```

---

## Architecture Options

### Option 1: Single Server (Simplest)

```
┌─────────────────────────────────────────┐
│         Intranet Server                 │
│  ┌─────────────────────────────────┐   │
│  │  Nginx (SSL Termination)        │   │
│  │  Port 443                        │   │
│  └───────────┬─────────────────────┘   │
│              │                          │
│  ┌───────────▼──────┐  ┌──────────┐   │
│  │  Frontend        │  │  Backend │   │
│  │  (Static Files)  │  │  :8000   │   │
│  └──────────────────┘  └──────────┘   │
└─────────────────────────────────────────┘
         │
         ▼
   [Internal Network]
         │
    ┌────┴────┐
    │   DNS   │
    │ migration-agent.company.local
    └─────────┘
```

**Pros:** Simple, easy to maintain, low cost
**Cons:** Single point of failure, limited scalability
**Use for:** <100 users, development/testing

### Option 2: Load Balanced (Recommended)

```
                [Internal Network]
                        │
                   ┌────▼────┐
                   │ Load    │
                   │ Balancer│
                   └─┬───┬───┘
           ┌─────────┘   └─────────┐
           │                       │
    ┌──────▼──────┐        ┌──────▼──────┐
    │  Server 1   │        │  Server 2   │
    │  ┌────────┐ │        │  ┌────────┐ │
    │  │Nginx   │ │        │  │Nginx   │ │
    │  │Frontend│ │        │  │Frontend│ │
    │  │Backend │ │        │  │Backend │ │
    │  └────────┘ │        │  └────────┘ │
    └─────────────┘        └─────────────┘
           │                       │
           └───────────┬───────────┘
                       │
                ┌──────▼──────┐
                │  Shared     │
                │  Storage    │
                │  (NFS/EFS)  │
                └─────────────┘
```

**Pros:** High availability, horizontal scaling
**Cons:** More complex, higher cost
**Use for:** >100 users, production

### Option 3: Kubernetes (Enterprise)

```
┌────────────────────────────────────────┐
│        Kubernetes Cluster               │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │  Ingress Controller (Nginx)     │  │
│  │  SSL Termination                │  │
│  └───────────┬─────────────────────┘  │
│              │                         │
│  ┌───────────▼──────┐  ┌──────────┐  │
│  │ Frontend Service │  │ Backend  │  │
│  │ (Deployment)     │  │ Service  │  │
│  │ Replicas: 2      │  │ Replicas:│  │
│  └──────────────────┘  │ 3        │  │
│                        └──────────┘  │
│                                      │
│  ┌─────────────────────────────────┐ │
│  │  PersistentVolume (Artifacts)   │ │
│  └─────────────────────────────────┘ │
└────────────────────────────────────────┘
```

**Pros:** Auto-scaling, self-healing, declarative config
**Cons:** Complex setup, requires K8s expertise
**Use for:** Large enterprise, multi-region

---

## Security Considerations

### 1. Network Security

**Firewall Rules:**
```bash
# Allow HTTPS from internal network only
sudo ufw allow from 10.0.0.0/8 to any port 443 proto tcp

# Allow SSH from admin network only
sudo ufw allow from 10.10.10.0/24 to any port 22 proto tcp

# Deny all other incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

**Network Segmentation:**
```
Internal Network: 10.0.0.0/8
├── User Network: 10.1.0.0/16 → Can access web UI
├── Admin Network: 10.10.0.0/16 → Can access servers
└── Database Network: 10.20.0.0/16 → PostgreSQL sources
```

### 2. Application Security

**Environment Variables (Never commit these!):**
```bash
# .env.production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# CORS - restrict to internal domains
ALLOWED_ORIGINS=https://migration-agent.company.local

# Security
SECRET_KEY=<generate-strong-random-key-here>

# Rate limiting
RATE_LIMIT_PER_MINUTE=100

# Session timeout (1 hour)
SESSION_TIMEOUT_SECONDS=3600
```

**Generate Secure Keys:**
```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. Authentication & Authorization

**Option A: LDAP Integration (Recommended)**

Add to backend/auth.py:
```python
from ldap3 import Server, Connection, ALL

def authenticate_ldap(username: str, password: str) -> bool:
    server = Server('ldap://ldap.company.local:389', get_info=ALL)
    conn = Connection(
        server,
        user=f'uid={username},ou=users,dc=company,dc=local',
        password=password
    )
    return conn.bind()
```

**Option B: Active Directory**

```python
import ldap

def authenticate_ad(username: str, password: str) -> bool:
    conn = ldap.initialize('ldap://ad.company.local')
    try:
        conn.simple_bind_s(f'{username}@company.local', password)
        return True
    except ldap.INVALID_CREDENTIALS:
        return False
```

**Option C: SSO (SAML/OAuth)**

Configure with your internal IdP (Okta, Azure AD, etc.)

### 4. Data Security

**Encryption at Rest:**
```bash
# Use encrypted volumes
# LUKS for Linux
sudo cryptsetup luksFormat /dev/sdb
sudo cryptsetup open /dev/sdb encrypted_vol
sudo mkfs.ext4 /dev/mapper/encrypted_vol
sudo mount /dev/mapper/encrypted_vol /app/artifacts
```

**Encryption in Transit:**
- SSL/TLS for all web traffic (HTTPS)
- PostgreSQL SSL connections (sslmode=require)
- Snowflake uses SSL by default

**Audit Logging:**
```python
# Add to logger.py
def log_user_action(user: str, action: str, details: dict):
    logger.info(
        "user_action",
        user=user,
        action=action,
        details=details,
        timestamp=datetime.utcnow().isoformat(),
        ip_address=request.client.host
    )
```

---

## Step-by-Step Deployment

### Step 1: Prepare Server

```bash
# 1.1 Login to intranet server
ssh admin@migration-server.company.local

# 1.2 Update system
sudo apt update && sudo apt upgrade -y

# 1.3 Install prerequisites
sudo apt install -y git curl wget vim ufw fail2ban

# 1.4 Create application user
sudo useradd -m -s /bin/bash migration
sudo usermod -aG docker migration

# 1.5 Create directories
sudo mkdir -p /opt/migration-agent
sudo mkdir -p /var/log/migration-agent
sudo mkdir -p /data/migration-agent/{artifacts,temp,logs}
sudo chown -R migration:migration /opt/migration-agent /var/log/migration-agent /data/migration-agent
```

### Step 2: Deploy Application

```bash
# 2.1 Switch to migration user
sudo su - migration

# 2.2 Clone repository (use internal GitLab/GitHub Enterprise)
cd /opt/migration-agent
git clone https://github.company.local/infrastructure/postgress-to-snowflake-migration-agent.git .

# 2.3 Create production environment file
cat > .env.production << 'EOF'
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://migration-agent.company.local
SECRET_KEY=YOUR_SECRET_KEY_HERE
ARTIFACTS_PATH=/data/migration-agent/artifacts
TEMP_PATH=/data/migration-agent/temp
EOF

# 2.4 Set proper permissions
chmod 600 .env.production
```

### Step 3: Configure Nginx

```bash
# 3.1 Create Nginx configuration
sudo tee /etc/nginx/sites-available/migration-agent << 'EOF'
# Rate limiting
limit_req_zone $binary_remote_addr zone=migration_limit:10m rate=10r/s;

upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name migration-agent.company.local;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name migration-agent.company.local;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/migration-agent.crt;
    ssl_certificate_key /etc/ssl/private/migration-agent.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/migration-agent-access.log;
    error_log /var/log/nginx/migration-agent-error.log;

    # Frontend - static files
    location / {
        root /opt/migration-agent/frontend/dist;
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    # Backend API
    location /api {
        limit_req zone=migration_limit burst=20 nodelay;
        
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running migrations
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check
    location /health {
        proxy_pass http://backend;
        access_log off;
    }

    # Artifacts download
    location /artifacts {
        internal;
        alias /data/migration-agent/artifacts;
    }
}
EOF

# 3.2 Enable site
sudo ln -s /etc/nginx/sites-available/migration-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4: Deploy with Docker Compose

```bash
# 4.1 Create production docker-compose file
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
      target: backend
    container_name: migration-agent-backend
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - /data/migration-agent/artifacts:/app/artifacts
      - /data/migration-agent/temp:/app/temp
      - /data/migration-agent/logs:/app/logs
    networks:
      - migration-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    build:
      context: .
      dockerfile: Dockerfile
      target: frontend
    container_name: migration-agent-frontend
    restart: unless-stopped
    volumes:
      - frontend-dist:/app/dist:ro
    networks:
      - migration-network

networks:
  migration-network:
    driver: bridge

volumes:
  frontend-dist:
EOF

# 4.2 Build and start services
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 4.3 Verify services are running
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### Step 5: Create Systemd Service

```bash
# 5.1 Create systemd service file
sudo tee /etc/systemd/system/migration-agent.service << 'EOF'
[Unit]
Description=PostgreSQL to Snowflake Migration Agent
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/migration-agent
User=migration
Group=migration

ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
ExecReload=/usr/local/bin/docker-compose -f docker-compose.prod.yml restart

TimeoutStartSec=0
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# 5.2 Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable migration-agent
sudo systemctl start migration-agent
sudo systemctl status migration-agent
```

### Step 6: Configure DNS

```bash
# 6.1 Add DNS entry (work with your IT team)
# Internal DNS Server: Add A record
migration-agent.company.local → 10.x.x.x

# 6.2 Or add to /etc/hosts on client machines
10.x.x.x    migration-agent.company.local
```

### Step 7: Verify Deployment

```bash
# 7.1 Check services
sudo systemctl status migration-agent
docker ps

# 7.2 Check logs
docker-compose -f docker-compose.prod.yml logs backend
tail -f /var/log/nginx/migration-agent-access.log

# 7.3 Test endpoints
curl https://migration-agent.company.local/health
curl https://migration-agent.company.local/api/v1/migrations

# 7.4 Access web UI
# Open browser: https://migration-agent.company.local
```

---

## Network Configuration

### Firewall Configuration

```bash
# Frontend/Nginx server
sudo ufw allow from 10.0.0.0/8 to any port 443 proto tcp
sudo ufw allow from 10.10.0.0/16 to any port 22 proto tcp

# Backend server (if separate)
sudo ufw allow from <frontend_ip> to any port 8000 proto tcp

# Database connections (PostgreSQL sources)
# Allow outbound to database network
sudo ufw allow out to 10.20.0.0/16 port 5432 proto tcp

# Snowflake (outbound HTTPS)
sudo ufw allow out 443/tcp

# Okta (outbound HTTPS)
sudo ufw allow out 443/tcp

sudo ufw enable
sudo ufw status numbered
```

### Load Balancer Configuration

**HAProxy Example:**
```bash
# /etc/haproxy/haproxy.cfg
frontend migration_frontend
    bind *:443 ssl crt /etc/ssl/certs/migration-agent.pem
    mode http
    default_backend migration_backend

backend migration_backend
    mode http
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200
    
    server server1 10.x.x.1:443 check ssl verify none
    server server2 10.x.x.2:443 check ssl verify none
    
    # Session stickiness
    cookie SERVERID insert indirect nocache
```

### Reverse Proxy Headers

Ensure proper forwarding:
```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Port $server_port;
```

---

## Monitoring & Maintenance

### 1. Health Checks

**Application Health:**
```bash
# Create health check script
cat > /opt/migration-agent/health-check.sh << 'EOF'
#!/bin/bash
HEALTH_URL="https://migration-agent.company.local/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✅ Application is healthy"
    exit 0
else
    echo "❌ Application is unhealthy (HTTP $RESPONSE)"
    # Send alert
    /usr/local/bin/send-alert.sh "Migration Agent Down"
    exit 1
fi
EOF

chmod +x /opt/migration-agent/health-check.sh

# Add to crontab
crontab -e
*/5 * * * * /opt/migration-agent/health-check.sh
```

### 2. Log Management

**Centralize Logs:**
```bash
# Configure rsyslog to forward to central server
cat >> /etc/rsyslog.d/50-migration-agent.conf << 'EOF'
# Forward migration agent logs
$ModLoad imfile
$InputFileName /data/migration-agent/logs/run_log.ndjson
$InputFileTag migration-agent:
$InputFileStateFile stat-migration-agent
$InputFileSeverity info
$InputFileFacility local7
$InputRunFileMonitor

local7.* @@syslog.company.local:514
EOF

sudo systemctl restart rsyslog
```

**Log Rotation:**
```bash
# /etc/logrotate.d/migration-agent
/data/migration-agent/logs/*.ndjson {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 migration migration
    sharedscripts
    postrotate
        docker-compose -f /opt/migration-agent/docker-compose.prod.yml restart backend > /dev/null 2>&1 || true
    endscript
}
```

### 3. Backup Strategy

**Artifacts Backup:**
```bash
# Daily backup script
cat > /opt/migration-agent/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/migration-agent"
DATE=$(date +%Y%m%d)

# Create backup
tar -czf $BACKUP_DIR/artifacts-$DATE.tar.gz /data/migration-agent/artifacts

# Keep only last 30 days
find $BACKUP_DIR -name "artifacts-*.tar.gz" -mtime +30 -delete

# Sync to backup server
rsync -avz $BACKUP_DIR/ backup-server:/backups/migration-agent/
EOF

chmod +x /opt/migration-agent/backup.sh

# Schedule daily at 2 AM
crontab -e
0 2 * * * /opt/migration-agent/backup.sh
```

### 4. Prometheus Metrics

Add metrics endpoint to backend:
```python
# backend/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

migration_counter = Counter('migrations_total', 'Total migrations', ['status'])
migration_duration = Histogram('migration_duration_seconds', 'Migration duration')
active_migrations = Gauge('active_migrations', 'Active migrations')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Prometheus Config:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'migration-agent'
    static_configs:
      - targets: ['migration-agent.company.local:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 5. Alerts

**Email Alerts:**
```bash
# Install mailutils
sudo apt install -y mailutils

# Create alert script
cat > /usr/local/bin/send-alert.sh << 'EOF'
#!/bin/bash
MESSAGE=$1
echo "$MESSAGE" | mail -s "[ALERT] Migration Agent" it-team@company.local
EOF

chmod +x /usr/local/bin/send-alert.sh
```

**Slack Alerts:**
```bash
#!/bin/bash
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
MESSAGE=$1

curl -X POST $SLACK_WEBHOOK \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"🚨 $MESSAGE\"}"
```

---

## Troubleshooting

### Common Issues

**1. Application Won't Start**
```bash
# Check Docker status
sudo systemctl status docker
docker ps -a

# Check logs
docker-compose -f docker-compose.prod.yml logs

# Rebuild containers
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

**2. Cannot Access Web UI**
```bash
# Check Nginx status
sudo systemctl status nginx
sudo nginx -t

# Check SSL certificate
openssl x509 -in /etc/ssl/certs/migration-agent.crt -text -noout

# Check firewall
sudo ufw status
sudo iptables -L

# Check DNS resolution
nslookup migration-agent.company.local
ping migration-agent.company.local
```

**3. Database Connection Failures**
```bash
# Test PostgreSQL connectivity from server
psql -h postgres-server -p 5432 -U user -d database

# Check network routes
traceroute postgres-server

# Check firewall rules on database server
# Allow migration agent IP
```

**4. High Memory Usage**
```bash
# Check container stats
docker stats

# Limit container resources
# Edit docker-compose.prod.yml:
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
```

**5. Disk Space Full**
```bash
# Check disk usage
df -h
du -sh /data/migration-agent/*

# Clean old artifacts
find /data/migration-agent/artifacts -type f -mtime +30 -delete

# Clean Docker
docker system prune -a --volumes
```

---

## Maintenance Tasks

### Weekly Tasks

```bash
# 1. Check logs for errors
tail -100 /var/log/migration-agent/run_log.ndjson | grep ERROR

# 2. Verify backups
ls -lh /backup/migration-agent/

# 3. Check disk space
df -h /data/migration-agent

# 4. Review security logs
grep "401\|403\|500" /var/log/nginx/migration-agent-access.log
```

### Monthly Tasks

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Update Docker images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 3. Review and rotate logs
sudo logrotate -f /etc/logrotate.d/migration-agent

# 4. Security audit
sudo lynis audit system
```

### Quarterly Tasks

```bash
# 1. Review user access
# Audit who has access and remove inactive users

# 2. Update SSL certificates
# Renew before expiration

# 3. Performance review
# Analyze metrics and optimize if needed

# 4. Disaster recovery test
# Restore from backup and verify
```

---

## Quick Reference Commands

```bash
# Start application
sudo systemctl start migration-agent

# Stop application
sudo systemctl stop migration-agent

# Restart application
sudo systemctl restart migration-agent

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check health
curl https://migration-agent.company.local/health

# Rebuild and deploy
cd /opt/migration-agent
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Clean old artifacts
find /data/migration-agent/artifacts -mtime +30 -delete

# Check disk space
df -h /data/migration-agent
```

---

## Support Contacts

- **Application Issues:** IT-Support@company.local
- **Network/Firewall:** Network-Team@company.local
- **Database Access:** DBA-Team@company.local
- **Security:** Security-Team@company.local

---

**For additional help, see:**
- [Getting Started Guide](GETTING_STARTED.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Architecture Document](ARCHITECTURE.md)
