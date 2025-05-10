#!/bin/bash

# Set the API base URL
API_URL="http://localhost:8000/api/v1"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Mock JWT token for testing
MOCK_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

echo -e "${YELLOW}=======================================================${NC}"
echo -e "${YELLOW}        Simple API Test Script                        ${NC}"
echo -e "${YELLOW}=======================================================${NC}"
echo

# Test the root endpoint
echo -e "${YELLOW}Testing Root Endpoint${NC}"
ROOT_RESPONSE=$(curl -s --connect-timeout 5 -m 10 http://localhost:8000/)
if [[ $ROOT_RESPONSE == *"AD-Rapport Generator API"* ]]; then
  echo -e "${GREEN}✓ Root endpoint working${NC}"
else
  echo -e "${RED}✗ Root endpoint failed${NC}"
  echo $ROOT_RESPONSE
fi
echo

# Test Auth endpoint
echo -e "${YELLOW}Testing Auth Endpoint${NC}"
AUTH_RESPONSE=$(curl -s --connect-timeout 5 -m 10 -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $AUTH_RESPONSE == *"user_id"* ]]; then
  echo -e "${GREEN}✓ Auth endpoint working${NC}"
else
  echo -e "${RED}✗ Auth endpoint failed${NC}"
  echo $AUTH_RESPONSE
fi
echo

# Test report templates endpoint
echo -e "${YELLOW}Testing Report Templates Endpoint${NC}"
TEMPLATES_RESPONSE=$(curl -s --connect-timeout 5 -m 10 -X GET "$API_URL/reports/templates" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $TEMPLATES_RESPONSE == *"staatvandienst"* ]]; then
  echo -e "${GREEN}✓ Report templates endpoint working${NC}"
else
  echo -e "${RED}✗ Report templates endpoint failed${NC}"
  echo $TEMPLATES_RESPONSE
fi
echo

echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}          Simple API Test Completed                    ${NC}"
echo -e "${YELLOW}=======================================================${NC}"