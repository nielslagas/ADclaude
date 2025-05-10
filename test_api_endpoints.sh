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
echo -e "${YELLOW}        AD-Rapport Generator API Test Script          ${NC}"
echo -e "${YELLOW}=======================================================${NC}"
echo

# Test the root endpoint
echo -e "${YELLOW}Testing Root Endpoint${NC}"
ROOT_RESPONSE=$(curl -s http://localhost:8000/)
if [[ $ROOT_RESPONSE == *"AD-Rapport Generator API"* ]]; then
  echo -e "${GREEN}✓ Root endpoint working${NC}"
else
  echo -e "${RED}✗ Root endpoint failed${NC}"
  echo $ROOT_RESPONSE
fi
echo

# Test Auth endpoint
echo -e "${YELLOW}Testing Auth Endpoint${NC}"
AUTH_RESPONSE=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $AUTH_RESPONSE == *"user_id"* ]]; then
  echo -e "${GREEN}✓ Auth endpoint working${NC}"
else
  echo -e "${RED}✗ Auth endpoint failed${NC}"
  echo $AUTH_RESPONSE
fi
echo

# Test cases endpoint
echo -e "${YELLOW}Testing Cases Endpoint${NC}"
CASES_RESPONSE=$(curl -s --connect-timeout 5 -m 10 -X GET "$API_URL/cases/" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $CASES_RESPONSE == "["* || $CASES_RESPONSE == "[]" ]]; then
  echo -e "${GREEN}✓ Cases endpoint working${NC}"
else
  echo -e "${RED}✗ Cases endpoint failed${NC}"
  echo $CASES_RESPONSE
fi
echo

# Test creating a case
echo -e "${YELLOW}Testing Case Creation${NC}"
TIMESTAMP=$(date +%s)
CREATE_CASE_RESPONSE=$(curl -s -X POST "$API_URL/cases/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MOCK_TOKEN" \
  -d "{\"title\":\"Test Case $TIMESTAMP\",\"description\":\"This is a test case\"}")

if [[ $CREATE_CASE_RESPONSE == *"id"* && $CREATE_CASE_RESPONSE == *"Test Case"* ]]; then
  echo -e "${GREEN}✓ Case creation successful${NC}"
  # Extract case ID for subsequent requests
  CASE_ID=$(echo $CREATE_CASE_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
  echo "Case ID: $CASE_ID"
else
  echo -e "${RED}✗ Case creation failed${NC}"
  echo $CREATE_CASE_RESPONSE
  exit 1
fi
echo

# Test getting a specific case
echo -e "${YELLOW}Testing Get Specific Case${NC}"
GET_CASE_RESPONSE=$(curl -s -X GET "$API_URL/cases/$CASE_ID" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $GET_CASE_RESPONSE == *"id"* && $GET_CASE_RESPONSE == *"Test Case"* ]]; then
  echo -e "${GREEN}✓ Get specific case successful${NC}"
else
  echo -e "${RED}✗ Get specific case failed${NC}"
  echo $GET_CASE_RESPONSE
fi
echo

# Test getting report templates
echo -e "${YELLOW}Testing Report Templates Endpoint${NC}"
TEMPLATES_RESPONSE=$(curl -s -X GET "$API_URL/reports/templates/" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $TEMPLATES_RESPONSE == *"staatvandienst"* ]]; then
  echo -e "${GREEN}✓ Report templates endpoint working${NC}"
else
  echo -e "${RED}✗ Report templates endpoint failed${NC}"
  echo $TEMPLATES_RESPONSE
fi
echo

# Test getting case documents (will be empty)
echo -e "${YELLOW}Testing Case Documents Endpoint${NC}"
DOCUMENTS_RESPONSE=$(curl -s -X GET "$API_URL/documents/case/$CASE_ID/" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $DOCUMENTS_RESPONSE == "["* || $DOCUMENTS_RESPONSE == "[]" ]]; then
  echo -e "${GREEN}✓ Case documents endpoint working${NC}"
else
  echo -e "${RED}✗ Case documents endpoint failed${NC}"
  echo $DOCUMENTS_RESPONSE
fi
echo

# Test getting case reports (will be empty)
echo -e "${YELLOW}Testing Case Reports Endpoint${NC}"
REPORTS_RESPONSE=$(curl -s -X GET "$API_URL/reports/case/$CASE_ID/" \
  -H "Authorization: Bearer $MOCK_TOKEN")

if [[ $REPORTS_RESPONSE == "["* || $REPORTS_RESPONSE == "[]" ]]; then
  echo -e "${GREEN}✓ Case reports endpoint working${NC}"
else
  echo -e "${RED}✗ Case reports endpoint failed${NC}"
  echo $REPORTS_RESPONSE
fi
echo

# Clean up - delete the test case
echo -e "${YELLOW}Cleaning Up - Deleting Test Case${NC}"
DELETE_CASE_RESPONSE=$(curl -s -X DELETE "$API_URL/cases/$CASE_ID" \
  -H "Authorization: Bearer $MOCK_TOKEN" -o /dev/null -w "%{http_code}")

if [[ $DELETE_CASE_RESPONSE == "204" ]]; then
  echo -e "${GREEN}✓ Case deletion successful${NC}"
else
  echo -e "${RED}✗ Case deletion failed${NC}"
  echo "HTTP Status: $DELETE_CASE_RESPONSE"
fi
echo

echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}          API Endpoint Testing Completed                ${NC}"
echo -e "${YELLOW}=======================================================${NC}"