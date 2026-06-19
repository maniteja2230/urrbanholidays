#!/bin/bash
# ═══════════════════════════════════════════════════════
#  Urban Holidays – One-Command Server Setup Script
#  Run on a fresh Ubuntu 22.04 VPS as root
#  Usage: bash deploy.sh
# ═══════════════════════════════════════════════════════

set -e  # Exit on any error

echo "╔══════════════════════════════════════════╗"
echo "║   Urban Holidays – Auto Deploy Script    ║"
echo "╚══════════════════════════════════════════╝"

# ── 1. Update System ──────────────────────────────────
echo ""
echo "📦 [1/10] Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq

# ── 2. Install Required Software ─────────────────────
echo "🔧 [2/10] Installing Nginx, Python, PostgreSQL..."
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    nginx \
    postgresql postgresql-contrib \
    certbot python3-certbot-nginx \
    git curl wget \
    build-essential libpq-dev

# ── 3. Create App Directory ───────────────────────────
echo "📁 [3/10] Creating application directory..."
mkdir -p /var/www/urbanholidays
mkdir -p /var/log/urbanholidays

# ── 4. Configure PostgreSQL ───────────────────────────
echo "🐘 [4/10] Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'uh_user') THEN
    CREATE USER uh_user WITH PASSWORD 'UH@Secure2024!';
  END IF;
END \$\$;

SELECT 'CREATE DATABASE urbanholidays OWNER uh_user'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'urbanholidays')\gexec

GRANT ALL PRIVILEGES ON DATABASE urbanholidays TO uh_user;
EOF

echo "✅ PostgreSQL configured"
echo "   Database : urbanholidays"
echo "   User     : uh_user"
echo "   Password : UH@Secure2024!"
echo ""
echo "⚠️  IMPORTANT: Change this password in your .env file!"

# ── 5. Clone / Copy Application ───────────────────────
echo ""
echo "📥 [5/10] Cloning application from GitHub..."
echo "   Please enter your GitHub repo URL:"
read -p "   GitHub URL (e.g. https://github.com/yourname/urban-holidays): " GITHUB_URL

if [ -n "$GITHUB_URL" ]; then
    cd /var/www/urbanholidays
    git clone "$GITHUB_URL" .
else
    echo "   ⚠️  No URL provided — copy files manually to /var/www/urbanholidays"
fi

# ── 6. Python Virtual Environment ─────────────────────
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
cat > /var/www/urbanholidays/.env << 'ENVEOF'
# ════════════════════════════════════════
#  Urban Holidays – Environment Variables
#  EDIT THIS FILE with your actual values!
# ════════════════════════════════════════

SECRET_KEY=REPLACE_WITH_50_CHAR_RANDOM_STRING
DEBUG=False
ALLOWED_HOSTS=*

# Database (PostgreSQL on this server)
DATABASE_URL=postgres://uh_user:UH@Secure2024!@localhost:5432/urbanholidays

# Razorpay LIVE Keys
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_live_secret_key

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=yourbusiness@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Urban Holidays <yourbusiness@gmail.com>

# Site Settings
SITE_NAME=Urban Holidays
SITE_URL=https://yourdomain.com
VOUCHER_PRICE=149
VOUCHER_VALIDITY_DAYS=365
REFERRAL_BONUS=50
ENVEOF

echo "✅ .env file created at /var/www/urbanholidays/.env"
echo "⚠️  EDIT IT NOW: nano /var/www/urbanholidays/.env"

# ── 8. Django Setup ───────────────────────────────────
echo ""
echo "🗄️  [8/10] Running Django setup..."
cd /var/www/urbanholidays
venv/bin/python manage.py migrate --no-input
venv/bin/python manage.py collectstatic --no-input
venv/bin/python manage.py loaddata fixtures/sample_data.json || true
echo "✅ Database migrated, static files collected"

# ── 9. Install Systemd Service ────────────────────────
echo ""
echo "⚙️  [9/10] Installing Gunicorn systemd service..."
cp /var/www/urbanholidays/urbanholidays.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable urbanholidays
systemctl start urbanholidays
echo "✅ Gunicorn service started"

# ── 10. Configure Nginx ───────────────────────────────
echo ""
echo "🌐 [10/10] Configuring Nginx..."
cp /var/www/urbanholidays/nginx.conf /etc/nginx/sites-available/urbanholidays
ln -sf /etc/nginx/sites-available/urbanholidays /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default  # Remove default page
nginx -t && systemctl restart nginx
echo "✅ Nginx configured"

# ── Set Permissions ───────────────────────────────────
chown -R www-data:www-data /var/www/urbanholidays/media /var/www/urbanholidays/staticfiles || true
chmod -R 755 /var/www/urbanholidays

# ── Done ──────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              ✅ DEPLOYMENT COMPLETE!                 ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║  Next steps:                                         ║"
echo "║  1. Edit .env:  nano /var/www/urbanholidays/.env    ║"
echo "║  2. Edit nginx: nano /etc/nginx/sites-available/    ║"
echo "║                  urbanholidays (add your domain)    ║"
echo "║  3. Get SSL:    certbot --nginx -d yourdomain.com   ║"
echo "║  4. Admin:      python manage.py createsuperuser    ║"
echo "║  5. Restart:    systemctl restart urbanholidays     ║"
echo "║                                                      ║"
echo "║  Status check:  systemctl status urbanholidays      ║"
echo "║  View logs:     journalctl -u urbanholidays -f      ║"
echo "╚══════════════════════════════════════════════════════╝"
