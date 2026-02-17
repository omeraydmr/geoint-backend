# STRATYON - Google Ads API Integration Design Document

## 1. Application Overview

**Application Name:** STRATYON
**Company:** Internal Development Project
**Contact:** omer.aydemir078@gmail.com
**Date:** December 2024

## 2. Purpose

STRATYON is a geo-intelligence and digital marketing platform designed for the Turkish market. The application integrates with Google Ads API to provide keyword research and market analysis capabilities.

## 3. Google Ads API Usage

### 3.1 Services Used

| Service | Purpose |
|---------|---------|
| KeywordPlanIdeaService | Generate keyword ideas and retrieve search volume metrics |
| CustomerService | List accessible customer accounts |

### 3.2 Data Flow

```
User Request → STRATYON Backend → Google Ads API → Process Response → Store in Database → Display to User
```

### 3.3 API Operations

1. **Keyword Research**
   - Input: Seed keywords in Turkish
   - Output: Related keywords with search volume, competition, CPC
   - Location: Turkey (geo_target_constant: 2792)
   - Language: Turkish (language_constant: 1019)

2. **Account Access**
   - List accessible customer accounts
   - Validate API credentials

## 4. Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│  Python Backend  │────▶│  Google Ads API │
│   (Next.js)     │     │  (FastAPI)       │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   PostgreSQL     │
                        │   Database       │
                        └──────────────────┘
```

## 5. Security Measures

- OAuth 2.0 authentication with refresh tokens
- API credentials stored as environment variables
- No credentials exposed in client-side code
- Rate limiting implemented to respect API quotas
- All API calls logged for audit purposes

## 6. User Access

- **Access Type:** Internal users only (employees)
- **No external/public access** to Google Ads API features
- Authentication required for all API endpoints

## 7. Compliance

- We comply with Google Ads API Terms of Service
- We do not resell or redistribute Google Ads data
- Data is used solely for internal business analysis
- User data is handled according to GDPR requirements

## 8. Rate Limiting

- Maximum 15,000 operations per day (Basic Access)
- Implemented caching to minimize API calls
- Background job queue for batch operations

## 9. Contact Information

- **Technical Contact:** omer.aydemir078@gmail.com
- **MCC Account ID:** 519-334-5186

---

*Document Version: 1.0*
*Last Updated: December 2024*
