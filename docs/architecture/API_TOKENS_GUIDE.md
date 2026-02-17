# 🔑 API Tokens & Credentials Guide

Complete guide for obtaining all API keys required for STRATYON platform.

---

## 📋 Table of Contents

1. [AI/LLM APIs](#1-aillm-apis)
2. [SEO & Analytics APIs](#2-seo--analytics-apis)
3. [Google Ads API](#3-google-ads-api)
4. [Meta (Facebook/Instagram) Ads API](#4-meta-facebookinstagram-ads-api)
5. [Mapping API](#5-mapping-api)
6. [Quick Reference](#6-quick-reference)

---

## 1. AI/LLM APIs

### OpenAI API (GPT-4o-mini)

**Purpose:** AI strategy generation, content analysis

**Cost:** ~$0.15/1M input tokens, ~$0.60/1M output tokens

**How to get:**

1. Go to https://platform.openai.com/signup
2. Create account or sign in
3. Navigate to https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)
6. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-proj-xxxxxxxxxx
   ```

**Free Credits:** $5 free trial for new accounts

**Billing:** https://platform.openai.com/account/billing

---

### Anthropic API (Claude)

**Purpose:** AI strategy generation (cheaper alternative to OpenAI)

**Cost:** ~$0.25/1M tokens (Haiku model)

**How to get:**

1. Go to https://console.anthropic.com/
2. Sign up for an account
3. Navigate to https://console.anthropic.com/settings/keys
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)
6. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxx
   ```

**Free Credits:** None, requires payment method

**Billing:** https://console.anthropic.com/settings/billing

---

## 2. SEO & Analytics APIs

### DataForSEO

**Purpose:** Keyword research, SEO metrics, competitor analysis

**Cost:** Pay-as-you-go, ~$1/1000 keywords

**How to get:**

1. Go to https://app.dataforseo.com/register
2. Sign up (email + password)
3. Verify your email
4. Log in to https://app.dataforseo.com/
5. Get your credentials from dashboard
6. Add to `.env`:
   ```
   DATAFORSEO_LOGIN=your-email@example.com
   DATAFORSEO_PASSWORD=your-password
   ```

**Free Credits:** $1 bonus credit on signup

**Pricing:** https://dataforseo.com/pricing

**API Docs:** https://docs.dataforseo.com/

---

## 3. Google Ads API

**Purpose:** Keyword metrics, ad performance, search volume data

**Cost:** Free API access (you pay for actual ads)

**How to get:** (Multi-step process)

### Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Create a new project (e.g., "STRATYON")
3. Enable Google Ads API:
   - Go to https://console.cloud.google.com/apis/library
   - Search for "Google Ads API"
   - Click "Enable"

### Step 2: Create OAuth 2.0 Credentials

1. Go to https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name it (e.g., "STRATYON Desktop")
5. Download the JSON file
6. Note your `client_id` and `client_secret`

### Step 3: Get Developer Token

1. Go to https://ads.google.com/aw/apicenter
2. Sign in with your Google Ads account
3. Click "Get Started" under API Center
4. Fill out the form (describe your app)
5. Copy your Developer Token (appears as `xxxxxxxxxxx`)

### Step 4: Generate Refresh Token

Run this Python script:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID = "your-client-id.apps.googleusercontent.com"
CLIENT_SECRET = "your-client-secret"

SCOPES = ['https://www.googleapis.com/auth/adwords']

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
        }
    },
    scopes=SCOPES
)

credentials = flow.run_local_server(port=8080)
print(f"Refresh token: {credentials.refresh_token}")
```

### Step 5: Get Customer ID

1. Log in to your Google Ads account
2. Top right corner shows your Customer ID (format: `123-456-7890`)

### Step 6: Add to .env

```env
GOOGLE_ADS_DEVELOPER_TOKEN=xxxxxxxxxxxxxxxxxxx
GOOGLE_ADS_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=xxxxxxxxxxxxxx
GOOGLE_ADS_REFRESH_TOKEN=1//xxxxxxxxxxxxxxxxxxxx
GOOGLE_ADS_CUSTOMER_ID=123-456-7890
```

**Documentation:** https://developers.google.com/google-ads/api/docs/start

**Video Tutorial:** https://www.youtube.com/watch?v=zN6L2FIBYt0

---

## 4. Meta (Facebook/Instagram) Ads API

**Purpose:** Facebook/Instagram ad insights, audience data

**Cost:** Free API access (you pay for actual ads)

**How to get:**

### Step 1: Create Facebook App

1. Go to https://developers.facebook.com/apps/
2. Click "Create App"
3. Select "Business" type
4. Fill in app details
5. Copy your `App ID` and `App Secret`

### Step 2: Get Access Token

**Option A: Graph API Explorer (Short-lived - Testing)**
1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app from dropdown
3. Click "Get Access Token"
4. Select permissions:
   - `ads_read`
   - `ads_management`
   - `business_management`
5. Copy the access token

**Option B: Long-Lived Token (Production)**

Exchange short-lived for long-lived:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token? \
grant_type=fb_exchange_token& \
client_id=YOUR_APP_ID& \
client_secret=YOUR_APP_SECRET& \
fb_exchange_token=SHORT_LIVED_TOKEN"
```

**Option C: System User (Best for Production)**

1. Go to Meta Business Suite: https://business.facebook.com/
2. Settings → Users → System Users
3. Add system user
4. Assign assets (Ad Accounts)
5. Generate token with required permissions

### Step 3: Get Ad Account ID

1. Go to https://business.facebook.com/settings/ad-accounts
2. Find your Ad Account
3. ID format: `act_1234567890123456`

### Step 4: Add to .env

```env
META_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
META_APP_ID=1234567890123456
META_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
META_AD_ACCOUNT_ID=act_1234567890123456
```

**Documentation:** https://developers.facebook.com/docs/marketing-apis

**Token Debugger:** https://developers.facebook.com/tools/debug/accesstoken/

---

## 5. Mapping API

### Mapbox

**Purpose:** Interactive maps, geocoding, heatmap visualization

**Cost:** Free tier: 50,000 map loads/month

**How to get:**

1. Go to https://account.mapbox.com/auth/signup/
2. Sign up with email
3. Verify email
4. Go to https://account.mapbox.com/access-tokens/
5. Copy your "Default public token" or create a new one
6. Add to `.env`:
   ```
   MAPBOX_ACCESS_TOKEN=pk.eyJ1IjoieW91cixxxxxxxxxx
   ```

**Free Tier:** 50,000 loads/month

**Pricing:** https://www.mapbox.com/pricing

---

## 6. Quick Reference

### Required for Basic Functionality

| API | Required | Purpose | Free Tier |
|-----|----------|---------|-----------|
| **Mapbox** | ✅ Yes | Maps visualization | 50K loads/month |
| **OpenAI or Claude** | ✅ One required | AI strategy generation | $5 (OpenAI only) |
| **DataForSEO** | ⚠️ Recommended | SEO data | $1 credit |

### Optional (Advanced Features)

| API | Required | Purpose | Free Tier |
|-----|----------|---------|-----------|
| **Google Ads** | ❌ Optional | Keyword metrics, ad insights | Yes (API free) |
| **Meta Ads** | ❌ Optional | Facebook/Instagram insights | Yes (API free) |

---

## 📝 Environment Variables Template

Complete `.env` file with all tokens:

```env
# Application
APP_NAME=STRATYON
DEBUG=true
SECRET_KEY=your-super-secret-key-change-this
API_V1_PREFIX=/api/v1

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=stratyon
POSTGRES_PASSWORD=stratyon123
POSTGRES_DB=stratyon_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI/LLM APIs (at least one required)
OPENAI_API_KEY=sk-proj-xxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxx

# SEO & Analytics APIs
DATAFORSEO_LOGIN=your-email@example.com
DATAFORSEO_PASSWORD=your-password

# Google Ads API (optional)
GOOGLE_ADS_DEVELOPER_TOKEN=xxxxxxxxxxx
GOOGLE_ADS_CLIENT_ID=xxxx.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=xxxxxx
GOOGLE_ADS_REFRESH_TOKEN=1//xxxxx
GOOGLE_ADS_CUSTOMER_ID=123-456-7890

# Meta (Facebook/Instagram) Ads API (optional)
META_ACCESS_TOKEN=EAAxxxxxxxxxx
META_APP_ID=1234567890123456
META_APP_SECRET=xxxxxxxxxx
META_AD_ACCOUNT_ID=act_123456789

# Mapping API (required)
MAPBOX_ACCESS_TOKEN=pk.eyJ1IjoieW91xxxxxxxxxx

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
```

---

## 💰 Estimated Monthly Costs

### Minimum Setup (Basic Features)
- **Mapbox:** Free (under 50K loads)
- **OpenAI:** ~$10-20 (depending on usage)
- **Total:** $10-20/month

### Full Setup (All Features)
- **Mapbox:** Free (under 50K loads)
- **OpenAI or Claude:** ~$10-30
- **DataForSEO:** ~$50-100 (for 50K-100K keywords)
- **Google Ads API:** Free
- **Meta Ads API:** Free
- **Total:** $60-130/month

### With Microsoft for Startups
- Azure hosting: $0 (up to $150K credits)
- **Total:** Same as above for APIs

---

## 🔒 Security Best Practices

1. **Never commit `.env` to git**
   ```bash
   # Already in .gitignore
   .env
   .env.*
   ```

2. **Rotate tokens regularly**
   - Every 90 days for production
   - Immediately if compromised

3. **Use least-privilege access**
   - Google Ads: Request only needed scopes
   - Meta: Grant minimal permissions

4. **Monitor usage**
   - Set billing alerts
   - Check API dashboards weekly

5. **Use environment-specific tokens**
   - Development: Separate tokens
   - Production: Restricted tokens

---

## ❓ Troubleshooting

### "Invalid API Key" Error

1. Check for spaces in `.env` file
2. Ensure key hasn't expired
3. Verify permissions/scopes

### Google Ads "403 Forbidden"

1. Enable Google Ads API in Cloud Console
2. Check Developer Token status
3. Verify OAuth consent screen is configured

### Meta "Invalid Access Token"

1. Token may have expired (short-lived tokens last ~2 hours)
2. Generate long-lived or system user token
3. Check token at https://developers.facebook.com/tools/debug/accesstoken/

### Rate Limiting

- **Google Ads:** 10,000 requests/day default
- **Meta:** 200 calls/hour per user
- **DataForSEO:** Based on your plan
- **OpenAI:** 90,000 tokens/minute (Tier 1)

---

## 📚 Additional Resources

- **Google Ads API Quickstart:** https://developers.google.com/google-ads/api/docs/first-call/overview
- **Meta Marketing API Guide:** https://developers.facebook.com/docs/marketing-api/get-started
- **DataForSEO Tutorials:** https://dataforseo.com/apis
- **OpenAI Best Practices:** https://platform.openai.com/docs/guides/production-best-practices
- **Mapbox GL JS Docs:** https://docs.mapbox.com/mapbox-gl-js/

---

**Questions?** Open an issue or check the main README.md

**STRATYON** - Veriyi Stratejiye Dönüştüren Güç 🚀
