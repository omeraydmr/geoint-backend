#!/bin/bash
set -euo pipefail

# STRATYON Backend - Pull Secrets from AWS SSM Parameter Store
# Generates a .env file from stored parameters
#
# Usage: bash scripts/pull-secrets.sh [environment]
# Example: bash scripts/pull-secrets.sh prod
#
# Prerequisites:
#   - AWS CLI configured with appropriate IAM permissions
#   - Parameters stored under /stratyon/<env>/ in SSM Parameter Store
#
# To store a secret:
#   aws ssm put-parameter --name "/stratyon/prod/SECRET_KEY" --value "your-value" --type SecureString

ENV="${1:-prod}"
PARAM_PATH="/stratyon/${ENV}/"
ENV_FILE="/opt/stratyon/.env"

echo "Pulling secrets from SSM Parameter Store (${PARAM_PATH})..."

# Fetch all parameters under the path
PARAMS=$(aws ssm get-parameters-by-path \
    --path "$PARAM_PATH" \
    --with-decryption \
    --query "Parameters[*].[Name,Value]" \
    --output text 2>&1)

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to fetch parameters from SSM."
    echo "$PARAMS"
    exit 1
fi

if [ -z "$PARAMS" ]; then
    echo "WARNING: No parameters found under ${PARAM_PATH}"
    echo "Store parameters first:"
    echo "  aws ssm put-parameter --name '${PARAM_PATH}SECRET_KEY' --value 'your-value' --type SecureString"
    exit 1
fi

# Write parameters to .env file
echo "# Auto-generated from AWS SSM Parameter Store" > "$ENV_FILE"
echo "# Path: ${PARAM_PATH}" >> "$ENV_FILE"
echo "# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"

echo "$PARAMS" | while IFS=$'\t' read -r name value; do
    key=$(echo "$name" | sed "s|${PARAM_PATH}||")
    echo "${key}=${value}" >> "$ENV_FILE"
done

# Add production overrides
echo "" >> "$ENV_FILE"
echo "# Production overrides" >> "$ENV_FILE"
echo "ENVIRONMENT=production" >> "$ENV_FILE"
echo "DEBUG=false" >> "$ENV_FILE"
echo "POSTGRES_HOST=db" >> "$ENV_FILE"
echo "REDIS_URL=redis://redis:6379/0" >> "$ENV_FILE"

# Secure the file
chmod 600 "$ENV_FILE"

PARAM_COUNT=$(echo "$PARAMS" | wc -l)
echo "Successfully wrote ${PARAM_COUNT} parameters to ${ENV_FILE}"
