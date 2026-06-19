#!/bin/bash
# ═══════════════════════════════════════════════════════
#  Urban Holidays – One-Command Server Setup Script
#  Compatible: Ubuntu 22.04 LTS & Ubuntu 24.04 LTS
#  Usage: bash deploy.sh
# ═══════════════════════════════════════════════════════

set -e  # Exit on any error

echo "╔══════════════════════════════════════════╗"
echo "║   Urban Holidays – Auto Deploy Script    ║"
echo "╚══════════════════════════════════════════╝"

# ── Detect Ubuntu Version ─────────────────────────────
UBUNTU_VERSION=$(lsb_release -rs)
echo "🖥️  Detected Ubuntu: $UBUNTU_VERSION"

# ── 1. Update System ──────────────────────────────────
echo ""
echo "📦 [1/10] Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get upgrade -y -qq

# ── 2. Install Required Software ──────────────────────
echo "🔧 [2/10] Installing Nginx, Python, PostgreSQL..."

# Install Python based on Ubuntu version
if [[ "$UBUNTU_VERSION" == "24.04" ]]; then
    apt-get install -y -qq \
        python3 python3-pip python3-venv python3-dev \
        nginx \
        postgresql postgresql-contrib \
        certbot python3-certbot-nginx \
        git curl wget \
        build-essential libpq-dev \
        pkg-config
else
    # Ubuntu 22.04
    apt-get install -y -qq \
        python3 python3-pip python3-venv python3-dev \
        nginx \
        postgresql postgresql-contrib \
        certbot python3-certbot-nginx \
        git curl wget \
        build-essential libpq-dev
fi

echo "✅ System packages installed"

# ── 3. Create App Directory ───────────────────────────
echo ""
echo "📁 [3/10] Creating application directory..."
mkdir -p /var/www/urbanholidays
mkdir -p /var/log/urbanholidays

# ── 4. Configure PostgreSQL ───────────────────────────
echo ""
echo "🐘 [4/10] Setting up PostgreSQL database..."

# Start PostgreSQL (Ubuntu 24.04 uses different service name sometimes)
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql <<EOF
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'uh_user') THEN
    CREATE USER uh_user WITH PASSWORD 'UH@Secure2024!';
  END IF;
END \$\$;

SELECT 'CREATE DATABASE urbanholidays OWNER uh_user'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'urbanholidays')\gexec

GRANT ALL PRIVILEGES ON DATABASE urbanholidays TO uh_user;
ALTER DATABASE urbanholidays OWNER TO uh_user;
EOF

echo "✅ PostgreSQL configured"
echo "   Database : urbanholidays"
echo "   User     : uh_user"
echo "   Password : UH@Secure2024!  ← Change this in .env!"

# ── 5. Clone Application from GitHub ─────────────────
echo ""
echo "📥 [5/10] Cloning application from GitHub..."
echo "   Enter your GitHub repo URL:"
read -p "   GitHub URL (e.g. https://github.com/yourname/urban-holidays): " GITHUB_URL

if [ -n "$GITHUB_URL" ]; then
    cd /var/www/urbanholidays
    git clone "$GITHUB_URL" .
    echo "✅ Code cloned"
else
    echo "   ⚠️  Skipped — copy files manually to /var/www/urbanholidays"
fi

# ── 6. Python Virtual Environment ────────────────────
echo ""
echo "🐍 [6/10] Setting up Python virtual environment..."
cd /var/www/urbanholidays
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
echo "✅ Python packages installed"

# ── 7. Create .env File ───────────────────────────────
echo ""
echo "⚙️  [7/10] Creating environment configuration..."

# Auto-generate a secure secret key
SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

cat > /var/www/urbanholidays/.env << ENVEOF
# ════════════════════════════════════════════════
#  Urban Holidays – Production Environment Config
#  Edit values marked with ← EDIT THIS
# ════════════════════════════════════════════════

SECRET_KEY=$SECRET
DEBUG=False
ALLOWED_HOSTS=*

# Database (PostgreSQL — already configured)
DATABASE_URL=postgres://uh_user:UH@Secure2024!@localhost:5432/urbanholidays

# ← EDIT: Razorpay LIVE Keys (dashboard.razorpay.com)
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_live_secret_key

# ← EDIT: Gmail App Password
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=yourbusiness@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Urban Holidays <yourbusiness@gmail.com>

# ← EDIT: Your domain
SITE_URL=https://yourdomain.com
SITE_NAME=Urban Holidays
VOUCHER_PRICE=149
VOUCHER_VALIDITY_DAYS=365
REFERRAL_BONUS=50
ENVEOF

echo "✅ .env file created (SECRET_KEY auto-generated)"
echo "⚠️  Edit it now: nano /var/www/urbanholidays/.env"

# ── 8. Django Setup ───────────────────────────────────
echo ""
echo "🗄️  [8/10] Running Django setup..."
cd /var/www/urbanholidays
venv/bin/python manage.py migrate --no-input
venv/bin/python manage.py collectstatic --no-input
venv/bin/python manage.py loaddata fixtures/sample_data.json 2>/dev/null || true
echo "✅ Database migrated & static files collected"

# ── 9. Install Systemd Service ────────────────────────
echo ""
echo "⚙️  [9/10] Installing Gunicorn systemd service..."
cp /var/www/urbanholidays/urbanholidays.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable urbanholidays
systemctl start urbanholidays
sleep 2
systemctl is-active --quiet urbanholidays && echo "✅ Gunicorn service running" || echo "⚠️ Check: journalctl -u urbanholidays"

# ── 10. Configure Nginx ───────────────────────────────
echo ""
echo "🌐 [10/10] Configuring Nginx..."
cp /var/www/urbanholidays/nginx.conf /etc/nginx/sites-available/urbanholidays
ln -sf /etc/nginx/sites-available/urbanholidays /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx && echo "✅ Nginx configured"

# ── Set Permissions ───────────────────────────────────
chown -R www-data:www-data /var/www/urbanholidays/staticfiles 2>/dev/null || true
mkdir -p /var/www/urbanholidays/media
chown -R www-data:www-data /var/www/urbanholidays/media
chmod -R 755 /var/www/urbanholidays

# ── Done! ─────────────────────────────────────────────
IP=$(curl -s ifconfig.me 2>/dev/null || echo "your-server-ip")

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            ✅ DEPLOYMENT COMPLETE!                       ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Your site is accessible at: http://$IP         ║"
echo "║                                                          ║"
echo "║  REQUIRED NEXT STEPS:                                    ║"
echo "║                                                          ║"
echo "║  1. Edit secrets:                                        ║"
echo "║     nano /var/www/urbanholidays/.env                    ║"
echo "║                                                          ║"
echo "║  2. Point your domain DNS A record to: $IP      ║"
echo "║                                                          ║"
echo "║  3. Update Nginx with your domain:                       ║"
echo "║     nano /etc/nginx/sites-available/urbanholidays        ║"
echo "║     (replace yourdomain.com with your real domain)       ║"
echo "║     systemctl reload nginx                               ║"
echo "║                                                          ║"
echo "║  4. Get free SSL:                                        ║"
echo "║     certbot --nginx -d yourdomain.com -d www.yourdomain.com ║"
echo "║                                                          ║"
echo "║  5. Create admin account:                                ║"
echo "║     cd /var/www/urbanholidays                            ║"
echo "║     venv/bin/python manage.py createsuperuser            ║"
echo "║                                                          ║"
echo "║  USEFUL COMMANDS:                                        ║"
echo "║  systemctl status urbanholidays  → check app status      ║"
echo "║  journalctl -u urbanholidays -f  → live logs             ║"
echo "║  systemctl restart urbanholidays → restart app           ║"
echo "╚══════════════════════════════════════════════════════════╝"
