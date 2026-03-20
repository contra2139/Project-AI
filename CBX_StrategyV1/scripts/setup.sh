#!/bin/bash
set -e

# Production setup script for CBX Bot
echo "🚀 Starting CBX Bot production setup..."

# 1. Check .env exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
fi

# 2. Generate Secret Keys if they are still using placeholders
if grep -q "your-secret-key" .env; then
    APP_SECRET=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 64)
    # Using sed to replace placeholders
    sed -i "s/your-secret-key-min-32-chars/$APP_SECRET/" .env
    sed -i "s/your-jwt-secret-key-min-64-chars/$JWT_SECRET/" .env
    echo "✅ Generated unique APP_SECRET and JWT_SECRET"
fi

# 3. Validate Critical Environment Variables
required_vars=("BINANCE_API_KEY" "BINANCE_API_SECRET" "TELEGRAM_BOT_TOKEN" "TELEGRAM_ADMIN_USER_ID" "DB_PASSWORD" "REDIS_PASSWORD")
missing=0

for var in "${required_vars[@]}"; do
    if grep -q "your-$var" .env 2>/dev/null; then
        echo "⚠️  WARNING: $var is still using a placeholder value in .env"
        missing=$((missing + 1))
    fi
done

if [ $missing -gt 0 ]; then
    echo "❌ Setup incomplete. Please update .env with actual values."
    exit 1
fi

# 4. Create necessary directories
mkdir -p nginx/ssl nginx/logs
echo "✅ Directories created (nginx/ssl, nginx/logs)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Setup Complete!"
echo "Run 'docker-compose up -d' to start the application."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
