#!/bin/sh
set -e

echo "Installing required utilities..."
apk add --no-cache curl zip

echo "Waiting for Vespa config server to be ready..."
MAX_RETRIES=60
RETRY_COUNT=0

until curl -sf http://vespa:19071/state/v1/health > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: Vespa config server did not become ready in time"
    exit 1
  fi
  echo "Waiting for Vespa config server... (attempt $RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

echo "Vespa config server is ready!"
echo "Deploying application package..."

# Create a zip of the application package
cd /app/vespa
zip -r /tmp/vespa-app.zip .

# Deploy to Vespa
echo "Sending deployment request..."
HTTP_CODE=$(curl -s -w "%{http_code}" -o /tmp/deploy-response.json \
  --header "Content-Type: application/zip" \
  --data-binary @/tmp/vespa-app.zip \
  http://vespa:19071/application/v2/tenant/default/prepareandactivate)

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Application package deployed successfully!"
  cat /tmp/deploy-response.json
  echo ""
else
  echo "ERROR: Failed to deploy application package (HTTP $HTTP_CODE)"
  cat /tmp/deploy-response.json
  echo ""
  exit 1
fi

# Wait for application to be fully active
echo "Waiting for application to become active..."
MAX_WAIT=120
WAIT_COUNT=0

until curl -sf http://vespa:8080/ApplicationStatus > /dev/null 2>&1; do
  WAIT_COUNT=$((WAIT_COUNT + 1))
  if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "ERROR: Application did not become active in time"
    exit 1
  fi
  echo "Waiting for application to be active... (attempt $WAIT_COUNT/$MAX_WAIT)"
  sleep 2
done

echo "✓ Vespa application is fully deployed and active!"
echo "Ready to accept documents and queries."
