#!/bin/bash

# Set the API base URL
API_URL="http://localhost:8000/api/v1"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Testing AD-Rapport Generator API endpoints...${NC}"
echo

# Test the root endpoint
echo -e "${YELLOW}1. Testing root endpoint${NC}"
ROOT_RESPONSE=$(curl -s http://localhost:8000/)
if [[ $ROOT_RESPONSE == *"AD-Rapport Generator API"* ]]; then
  echo -e "${GREEN}✓ Root endpoint working${NC}"
else
  echo -e "${RED}✗ Root endpoint failed${NC}"
  echo $ROOT_RESPONSE
fi
echo

# Test login
echo -e "${YELLOW}2. Testing login endpoint${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}')

if [[ $LOGIN_RESPONSE == *"token"* ]]; then
  echo -e "${GREEN}✓ Login successful${NC}"
  # Extract token for subsequent requests
  TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
else
  echo -e "${RED}✗ Login failed${NC}"
  echo $LOGIN_RESPONSE
  exit 1
fi
echo

# Test cases endpoint
echo -e "${YELLOW}3. Testing cases endpoint${NC}"
CASES_RESPONSE=$(curl -s -X GET "$API_URL/cases" \
  -H "Authorization: Bearer $TOKEN")

if [[ $CASES_RESPONSE == "["* || $CASES_RESPONSE == "[]" ]]; then
  echo -e "${GREEN}✓ Cases endpoint working${NC}"
else
  echo -e "${RED}✗ Cases endpoint failed${NC}"
  echo $CASES_RESPONSE
fi
echo

# Test creating a case
echo -e "${YELLOW}4. Testing case creation${NC}"
CREATE_CASE_RESPONSE=$(curl -s -X POST "$API_URL/cases" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Test Case","description":"This is a test case"}')

if [[ $CREATE_CASE_RESPONSE == *"id"* && $CREATE_CASE_RESPONSE == *"Test Case"* ]]; then
  echo -e "${GREEN}✓ Case creation successful${NC}"
  # Extract case ID for subsequent requests
  CASE_ID=$(echo $CREATE_CASE_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
else
  echo -e "${RED}✗ Case creation failed${NC}"
  echo $CREATE_CASE_RESPONSE
  exit 1
fi
echo

# Test getting a specific case
echo -e "${YELLOW}5. Testing get specific case${NC}"
GET_CASE_RESPONSE=$(curl -s -X GET "$API_URL/cases/$CASE_ID" \
  -H "Authorization: Bearer $TOKEN")

if [[ $GET_CASE_RESPONSE == *"id"* && $GET_CASE_RESPONSE == *"Test Case"* ]]; then
  echo -e "${GREEN}✓ Get specific case successful${NC}"
else
  echo -e "${RED}✗ Get specific case failed${NC}"
  echo $GET_CASE_RESPONSE
fi
echo

# Test getting report templates
echo -e "${YELLOW}6. Testing report templates endpoint${NC}"
TEMPLATES_RESPONSE=$(curl -s -X GET "$API_URL/reports/templates" \
  -H "Authorization: Bearer $TOKEN")

if [[ $TEMPLATES_RESPONSE == *"staatvandienst"* ]]; then
  echo -e "${GREEN}✓ Report templates endpoint working${NC}"
else
  echo -e "${RED}✗ Report templates endpoint failed${NC}"
  echo $TEMPLATES_RESPONSE
fi
echo

# Test getting case documents (will be empty)
echo -e "${YELLOW}7. Testing case documents endpoint${NC}"
DOCUMENTS_RESPONSE=$(curl -s -X GET "$API_URL/documents/case/$CASE_ID" \
  -H "Authorization: Bearer $TOKEN")

if [[ $DOCUMENTS_RESPONSE == "["* || $DOCUMENTS_RESPONSE == "[]" ]]; then
  echo -e "${GREEN}✓ Case documents endpoint working${NC}"
else
  echo -e "${RED}✗ Case documents endpoint failed${NC}"
  echo $DOCUMENTS_RESPONSE
fi
echo

# Test getting case reports (will be empty)
echo -e "${YELLOW}8. Testing case reports endpoint${NC}"
REPORTS_RESPONSE=$(curl -s -X GET "$API_URL/reports/case/$CASE_ID" \
  -H "Authorization: Bearer $TOKEN")

if [[ $REPORTS_RESPONSE == "["* || $REPORTS_RESPONSE == "[]" ]]; then
  echo -e "${GREEN}✓ Case reports endpoint working${NC}"
else
  echo -e "${RED}✗ Case reports endpoint failed${NC}"
  echo $REPORTS_RESPONSE
fi
echo

# Clean up - delete the test case
echo -e "${YELLOW}9. Cleaning up - deleting test case${NC}"
DELETE_CASE_RESPONSE=$(curl -s -X DELETE "$API_URL/cases/$CASE_ID" \
  -H "Authorization: Bearer $TOKEN" -o /dev/null -w "%{http_code}")

if [[ $DELETE_CASE_RESPONSE == "204" ]]; then
  echo -e "${GREEN}✓ Case deletion successful${NC}"
else
  echo -e "${RED}✗ Case deletion failed${NC}"
  echo "HTTP Status: $DELETE_CASE_RESPONSE"
fi
echo

echo -e "${GREEN}End-to-end API tests completed!${NC}"