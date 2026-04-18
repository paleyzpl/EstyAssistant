#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# Etsy Assistant — Free Deployment Setup
# Automates: Fly.io app creation, Supabase schema, secrets, deploy
#
# Prerequisites (5 min of manual signup):
#   1. Fly.io account: https://fly.io/app/sign-up (with ProtonMail)
#   2. Supabase account: https://supabase.com (with ProtonMail)
#      - Create a new project
#      - Go to Project Settings > Database > Connection string (Session mode)
#      - Go to Project Settings > Storage > S3 Connection
#      - Create a bucket called "etsy-assistant-images"
#   3. Anthropic API key: https://console.anthropic.com
#   4. (Optional) Etsy developer account: https://www.etsy.com/developers
#
# After signup, install flyctl: curl -L https://fly.io/install.sh | sh
# Then run: ./scripts/setup-free.sh
# ──────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}==>${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# Check prerequisites
command -v flyctl >/dev/null 2>&1 || fail "flyctl not found. Install: curl -L https://fly.io/install.sh | sh"
flyctl auth whoami >/dev/null 2>&1 || fail "Not logged into Fly. Run: flyctl auth login"

APP_NAME="${APP_NAME:-etsy-assistant-$(whoami)-$(date +%s | tail -c 5)}"
info "Using app name: $APP_NAME"

# Prompt for secrets
read -p "Supabase project URL (e.g., https://abc.supabase.co): " SUPABASE_URL
read -p "Supabase database URL (from Project Settings > Database > Connection string): " SUPABASE_DB_URL
read -p "Supabase S3 access key ID: " SUPABASE_S3_ACCESS_KEY_ID
read -sp "Supabase S3 secret access key: " SUPABASE_S3_SECRET_ACCESS_KEY
echo
read -p "Supabase storage bucket name [etsy-assistant-images]: " S3_BUCKET
S3_BUCKET=${S3_BUCKET:-etsy-assistant-images}
read -sp "Anthropic API key: " ANTHROPIC_API_KEY
echo
read -p "Etsy API key (or press enter to skip): " ETSY_API_KEY
read -p "Frontend URL (your Vercel domain, or http://localhost:3000): " FRONTEND_URL
FRONTEND_URL=${FRONTEND_URL:-http://localhost:3000}

info "Creating Fly.io app..."
flyctl apps create "$APP_NAME" 2>/dev/null || warn "App $APP_NAME may already exist, continuing"

# Update fly.toml with app name
sed -i.bak "s/^app = .*/app = \"$APP_NAME\"/" fly.toml && rm fly.toml.bak

info "Setting Fly secrets..."
flyctl secrets set -a "$APP_NAME" \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    ETSY_API_KEY="${ETSY_API_KEY:-}" \
    FRONTEND_URL="$FRONTEND_URL" \
    SUPABASE_URL="$SUPABASE_URL" \
    SUPABASE_DB_URL="$SUPABASE_DB_URL" \
    SUPABASE_S3_ACCESS_KEY_ID="$SUPABASE_S3_ACCESS_KEY_ID" \
    SUPABASE_S3_SECRET_ACCESS_KEY="$SUPABASE_S3_SECRET_ACCESS_KEY" \
    S3_BUCKET="$S3_BUCKET" \
    CORS_ORIGINS="$FRONTEND_URL,http://localhost:3000"

info "Deploying to Fly.io..."
flyctl deploy -a "$APP_NAME" --config fly.toml

API_URL="https://$APP_NAME.fly.dev"

echo
ok "Deployment complete!"
echo "────────────────────────────────────"
echo "  App:     $APP_NAME"
echo "  API URL: $API_URL"
echo "────────────────────────────────────"
echo
info "Next steps:"
echo "  1. Test health: curl $API_URL/health"
echo "  2. Go to Vercel, connect your GitHub repo"
echo "  3. Set Vercel env: NEXT_PUBLIC_API_URL=$API_URL"
echo "  4. Deploy frontend (auto on git push)"
echo "  5. Update CORS: flyctl secrets set -a $APP_NAME CORS_ORIGINS=\"https://your-vercel-app.vercel.app\""
