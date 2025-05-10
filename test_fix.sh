#!/bin/bash

# Base URL for API
API_BASE="http://localhost:8000/api/v1"

# Test User Data
USER_ID="example_user_id"
CASE_ID="a31bfdf0-aaf6-4b75-9db3-0a52fc86d2b7"  # Valid case ID for example_user_id

# Auth Token - this is a fake token that will pass the basic verification
# The MVP implementation will extract example_user_id from this token
# or fallback to that value if decoding fails
AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNjkyODA1MTk4fQ.nL3TDvQFGIlOdCifWXvnfUmCcHpDhMG53LvKfnZlhLc"

# Test Document
TEST_DOC="test_simplified.txt"

echo "=== Testing Document Upload ==="
DOCUMENT_RESPONSE=$(curl -s -X POST "${API_BASE}/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "file=@${TEST_DOC}" \
  -F "case_id=${CASE_ID}")

echo "Document Upload Response:"
echo $DOCUMENT_RESPONSE

# Extract document ID from response
DOCUMENT_ID=$(echo $DOCUMENT_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)

echo "Document ID: $DOCUMENT_ID"

# Wait for document processing
echo "Waiting 10 seconds for document processing..."
sleep 10

# Check document status
echo "=== Checking Document Status ==="
DOC_STATUS=$(curl -s -X GET "${API_BASE}/documents/$DOCUMENT_ID" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")
echo "Document Status Response:"
echo $DOC_STATUS

# Create a report
echo "=== Creating Report ==="
REPORT_RESPONSE=$(curl -s -X POST "${API_BASE}/reports/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -d '{
    "title": "Test Report",
    "case_id": "'$CASE_ID'",
    "template_id": "staatvandienst",
    "document_ids": ["'$DOCUMENT_ID'"]
  }')

echo "Report Creation Response:"
echo $REPORT_RESPONSE

# Extract report ID from response
REPORT_ID=$(echo $REPORT_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)

echo "Report ID: $REPORT_ID"

# Wait for report generation
echo "Waiting 20 seconds for report generation..."
sleep 20

# Check report status
echo "=== Checking Report Status ==="
REPORT_STATUS=$(curl -s -X GET "${API_BASE}/reports/$REPORT_ID" \
  -H "Authorization: Bearer ${AUTH_TOKEN}")
echo "Report Status Response:"
echo $REPORT_STATUS